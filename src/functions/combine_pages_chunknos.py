"""WebApiSkill helper that zips ``pages`` and ``chunk_nos`` arrays together.

Ported verbatim from the parent accelerator's
``code/backend/batch/combine_pages_chunknos.py`` (commit
``5c99c241b3ef4f4bbbcfdcca0d4b4b3a405424c3``).

This function is self-contained -- it has no helper or third-party
dependencies beyond ``azure.functions`` -- so it works end-to-end in
spec 0001 without any stubbing.
"""

import json
import logging

import azure.functions as func

bp_combine_pages_and_chunknos = func.Blueprint()


@bp_combine_pages_and_chunknos.route(
    route="combine_pages_and_chunknos",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def combine_pages_and_chunknos(req: func.HttpRequest) -> func.HttpResponse:
    """Called by an Azure AI Search WebApiSkill.

    Expects a JSON payload with two arrays (``pages`` and ``chunk_nos``)
    and combines them into a single array of objects.
    """
    logging.info("Combine pages and chunk numbers function processed a request.")

    try:
        req_body = req.get_json()
        values = req_body.get("values", [])

        response_values = []

        for value in values:
            record_id = value.get("recordId")
            data = value.get("data", {})

            pages = data.get("pages", [])
            chunk_nos = data.get("chunk_nos", [])

            zipped_data = [
                {"page_text": page, "chunk_no": chunk}
                for page, chunk in zip(pages, chunk_nos)
            ]

            response_values.append(
                {
                    "recordId": record_id,
                    "data": {"pages_with_chunks": zipped_data},
                    "errors": None,
                    "warnings": None,
                }
            )

        return func.HttpResponse(
            body=json.dumps({"values": response_values}),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:
        logging.error("Error in combine_pages_and_chunknos function: %s", e)
        return func.HttpResponse(
            body=json.dumps(
                {
                    "values": [
                        {
                            "recordId": "error",
                            "data": {},
                            "errors": [{"message": str(e)}],
                            "warnings": [],
                        }
                    ]
                }
            ),
            mimetype="application/json",
            status_code=500,
        )
