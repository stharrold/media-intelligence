"""
Cloud Run/Cloud Functions entry point for the Media Intelligence Pipeline.

This module provides both HTTP endpoints (for Cloud Run) and event handlers
(for Cloud Functions) for processing audio files.
"""

import logging
import os

import functions_framework
from flask import Flask, jsonify, request
from google.cloud import error_reporting
from google.cloud import logging as cloud_logging

# Configure logging
if os.getenv("ENABLE_STRUCTURED_LOGGING", "true").lower() == "true":
    try:
        logging_client = cloud_logging.Client()
        logging_client.setup_logging()
    except Exception:
        pass  # Fall back to standard logging

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize error reporting
error_client = None
try:
    error_client = error_reporting.Client()
except Exception:
    logger.warning("Error reporting client not available")

# Flask app for Cloud Run
app = Flask(__name__)


def get_processor():
    """Get or create AudioProcessor instance."""
    from .audio_processor import AudioProcessor

    return AudioProcessor()


@app.route("/process", methods=["POST"])
def process_audio():
    """
    Process audio file from GCS.

    Request JSON:
    {
        "gcs_uri": "gs://bucket/path/to/audio.wav",
        "output_bucket": "output-bucket-name",  // Optional
        "config": {
            "language_code": "en-US",  // Optional
            "min_speakers": 2,          // Optional
            "max_speakers": 6,          // Optional
            "model": "long"             // long, short, telephony, video
        }
    }

    Response JSON:
    {
        "status": "success",
        "file_id": "20231201_123456_abc12345",
        "result_uri": "gs://output-bucket/results/{file_id}.json",
        "transcript_uri": "gs://output-bucket/transcripts/{file_id}.txt",
        "processing_time": 12.34,
        "cost_estimate": {
            "speech_to_text": 0.036,
            "situation_classification": 0.006,
            "storage": 0.001,
            "total": 0.043
        },
        "summary": {
            "duration": 60.5,
            "speaker_count": 2,
            "overall_situation": "meeting"
        }
    }

    Error Response:
    {
        "status": "error",
        "error": "Error message"
    }
    """
    try:
        # Parse request
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "error": "No JSON data provided"}), 400

        gcs_uri = data.get("gcs_uri")
        if not gcs_uri:
            return jsonify({"status": "error", "error": "gcs_uri is required"}), 400

        output_bucket = data.get("output_bucket")
        config = data.get("config", {})

        logger.info(f"Processing request for {gcs_uri}")

        # Process file
        processor = get_processor()
        result = processor.process_file(
            gcs_uri=gcs_uri,
            output_bucket=output_bucket,
            config=config,
        )

        # Check for errors
        if result.error:
            logger.error(f"Processing failed: {result.error}")
            if error_client:
                error_client.report(result.error)
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": result.error,
                        "file_id": result.file_id,
                    }
                ),
                500,
            )

        # Return success response
        return (
            jsonify(
                {
                    "status": "success",
                    "file_id": result.file_id,
                    "result_uri": result.gcs_output_uri,
                    "transcript_uri": result.transcript_uri,
                    "processing_time": round(result.processing_time, 2),
                    "cost_estimate": result.cost_estimate,
                    "summary": {
                        "duration": round(result.duration, 2),
                        "speaker_count": result.speaker_count,
                        "overall_situation": result.overall_situation,
                        "overall_situation_confidence": round(result.overall_situation_confidence, 2),
                        "segment_count": len(result.transcript_segments),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        if error_client:
            error_client.report_exception()
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/batch", methods=["POST"])
def process_batch():
    """
    Process multiple audio files.

    Request JSON:
    {
        "gcs_uris": [
            "gs://bucket/path/to/audio1.wav",
            "gs://bucket/path/to/audio2.wav"
        ],
        "output_bucket": "output-bucket-name",
        "config": {...}
    }

    Response JSON:
    {
        "status": "success",
        "results": [
            {...},  // Same as single file response
            {...}
        ],
        "summary": {
            "total": 2,
            "successful": 2,
            "failed": 0
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "error": "No JSON data provided"}), 400

        gcs_uris = data.get("gcs_uris", [])
        if not gcs_uris:
            return jsonify({"status": "error", "error": "gcs_uris is required"}), 400

        output_bucket = data.get("output_bucket")
        config = data.get("config", {})

        logger.info(f"Processing batch of {len(gcs_uris)} files")

        processor = get_processor()
        results = processor.process_batch(
            gcs_uris=gcs_uris,
            output_bucket=output_bucket,
            config=config,
        )

        # Build response
        response_results = []
        successful = 0
        failed = 0

        for result in results:
            if result.error:
                failed += 1
                response_results.append(
                    {
                        "gcs_uri": result.gcs_input_uri,
                        "status": "error",
                        "error": result.error,
                    }
                )
            else:
                successful += 1
                response_results.append(
                    {
                        "gcs_uri": result.gcs_input_uri,
                        "status": "success",
                        "file_id": result.file_id,
                        "result_uri": result.gcs_output_uri,
                        "transcript_uri": result.transcript_uri,
                    }
                )

        return (
            jsonify(
                {
                    "status": "success",
                    "results": response_results,
                    "summary": {
                        "total": len(gcs_uris),
                        "successful": successful,
                        "failed": failed,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Batch request failed: {str(e)}", exc_info=True)
        if error_client:
            error_client.report_exception()
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "media-intelligence"}), 200


@app.route("/ready", methods=["GET"])
def ready():
    """Readiness check endpoint."""
    # Could add checks for Speech API, Storage, etc.
    return jsonify({"status": "ready"}), 200


@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API info."""
    return (
        jsonify(
            {
                "service": "media-intelligence",
                "version": "1.0.0",
                "endpoints": {
                    "POST /process": "Process a single audio file",
                    "POST /batch": "Process multiple audio files",
                    "GET /health": "Health check",
                    "GET /ready": "Readiness check",
                },
            }
        ),
        200,
    )


# Cloud Functions entry point
@functions_framework.cloud_event
def process_audio_gcs(cloud_event):
    """
    Cloud Function triggered by Cloud Storage upload.

    Event data:
    {
        "bucket": "input-bucket",
        "name": "path/to/audio.wav",
        "metageneration": "1",
        "timeCreated": "2023-01-01T00:00:00.000Z",
        "updated": "2023-01-01T00:00:00.000Z"
    }
    """
    try:
        data = cloud_event.data

        bucket = data.get("bucket")
        name = data.get("name")

        if not bucket or not name:
            logger.error("Invalid event data: missing bucket or name")
            return

        gcs_uri = f"gs://{bucket}/{name}"
        logger.info(f"Cloud Function triggered for {gcs_uri}")

        # Check if file should be processed
        from .gcp_utils import is_supported_format

        if not is_supported_format(gcs_uri):
            logger.info(f"Skipping unsupported format: {gcs_uri}")
            return

        # Get output bucket from environment
        output_bucket = os.getenv("OUTPUT_BUCKET")
        if not output_bucket:
            logger.error("OUTPUT_BUCKET environment variable not set")
            return

        # Process file
        processor = get_processor()
        result = processor.process_file(
            gcs_uri=gcs_uri,
            output_bucket=output_bucket,
        )

        if result.error:
            logger.error(f"Processing failed: {result.error}")
            if error_client:
                error_client.report(result.error)
        else:
            logger.info(f"Processing complete: {result.gcs_output_uri}, " f"transcript: {result.transcript_uri}")

    except Exception as e:
        logger.error(f"Cloud Function failed: {str(e)}", exc_info=True)
        if error_client:
            error_client.report_exception()
        raise


# HTTP Cloud Function entry point
@functions_framework.http
def process_audio_http(request):
    """
    HTTP Cloud Function for processing audio.

    Same interface as /process endpoint.
    """
    # Reuse Flask app logic
    with app.test_request_context(
        path="/process",
        method="POST",
        data=request.get_data(),
        content_type="application/json",
    ):
        response = process_audio()
        return response


# Main entry point for Cloud Run
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
