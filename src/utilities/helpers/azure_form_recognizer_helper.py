import logging
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from .azure_credential_utils import get_azure_credential
import html
import traceback
from .env_helper import EnvHelper

logger = logging.getLogger(__name__)


class AzureFormRecognizerClient:
    def __init__(self) -> None:
        env_helper: EnvHelper = EnvHelper()

        self.AZURE_FORM_RECOGNIZER_ENDPOINT: str = (
            env_helper.AZURE_FORM_RECOGNIZER_ENDPOINT
        )
        if env_helper.AZURE_AUTH_TYPE == "rbac":
            self.document_analysis_client = DocumentAnalysisClient(
                endpoint=self.AZURE_FORM_RECOGNIZER_ENDPOINT,
                credential=get_azure_credential(env_helper.MANAGED_IDENTITY_CLIENT_ID),
                headers={
                    "x-ms-useragent": "chat-with-your-data-solution-accelerator/1.0.0"
                },
            )
        else:
            self.AZURE_FORM_RECOGNIZER_KEY: str = env_helper.AZURE_FORM_RECOGNIZER_KEY

            self.document_analysis_client = DocumentAnalysisClient(
                endpoint=self.AZURE_FORM_RECOGNIZER_ENDPOINT,
                credential=AzureKeyCredential(self.AZURE_FORM_RECOGNIZER_KEY),
                headers={
                    "x-ms-useragent": "chat-with-your-data-solution-accelerator/1.0.0"
                },
            )

    form_recognizer_role_to_html = {
        "title": "h1",
        "sectionHeading": "h2",
        "pageHeader": None,
        "pageFooter": None,
        "paragraph": "p",
    }

    def _table_to_html(self, table):
        table_html = "<table>"
        rows = [
            sorted(
                [cell for cell in table.cells if cell.row_index == i],
                key=lambda cell: cell.column_index,
            )
            for i in range(table.row_count)
        ]
        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = (
                    "th"
                    if (cell.kind == "columnHeader" or cell.kind == "rowHeader")
                    else "td"
                )
                cell_spans = ""
                if cell.column_span > 1:
                    cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span > 1:
                    cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html += "</tr>"
        table_html += "</table>"
        return table_html

    def begin_analyze_document_from_url(
        self, source_url: str, use_layout: bool = True, paragraph_separator: str = ""
    ):
        offset = 0
        page_map = []
        model_id = "prebuilt-layout" if use_layout else "prebuilt-read"

        try:
            logger.info("Method begin_analyze_document_from_url started")
            logger.info(f"Model ID selected: {model_id}")
            poller = self.document_analysis_client.begin_analyze_document_from_url(
                model_id, document_url=source_url
            )
            form_recognizer_results = poller.result()

            # (if using layout) mark all the positions of headers
            roles_start = {}
            roles_end = {}
            for paragraph in form_recognizer_results.paragraphs:
                # if paragraph.role!=None:
                para_start = paragraph.spans[0].offset
                para_end = paragraph.spans[0].offset + paragraph.spans[0].length
                roles_start[para_start] = (
                    paragraph.role if paragraph.role is not None else "paragraph"
                )
                roles_end[para_end] = (
                    paragraph.role if paragraph.role is not None else "paragraph"
                )

            for page_num, page in enumerate(form_recognizer_results.pages):
                tables_on_page = [
                    table
                    for table in form_recognizer_results.tables
                    if table.bounding_regions[0].page_number == page_num + 1
                ]

                # (if using layout) mark all positions of the table spans in the page
                page_offset = page.spans[0].offset
                page_length = page.spans[0].length
                table_chars = [-1] * page_length
                for table_id, table in enumerate(tables_on_page):
                    for span in table.spans:
                        # replace all table spans with "table_id" in table_chars array
                        for i in range(span.length):
                            idx = span.offset - page_offset + i
                            if idx >= 0 and idx < page_length:
                                table_chars[idx] = table_id

                # build page text by replacing charcters in table spans with table html and replace the characters corresponding to headers with html headers, if using layout
                page_text = ""
                added_tables = set()
                for idx, table_id in enumerate(table_chars):
                    if table_id == -1:
                        position = page_offset + idx
                        if position in roles_start.keys():
                            role = roles_start[position]
                            html_role = self.form_recognizer_role_to_html.get(role)
                            if html_role is not None:
                                page_text += f"<{html_role}>"
                        if position in roles_end.keys():
                            role = roles_end[position]
                            html_role = self.form_recognizer_role_to_html.get(role)
                            if html_role is not None:
                                page_text += f"</{html_role}>"

                        page_text += form_recognizer_results.content[page_offset + idx]

                    elif table_id not in added_tables:
                        page_text += self._table_to_html(tables_on_page[table_id])
                        added_tables.add(table_id)

                page_text += " "
                page_map.append(
                    {"page_number": page_num, "offset": offset, "page_text": page_text}
                )
                offset += len(page_text)

            return page_map
        except Exception as e:
            logger.exception(f"Exception in begin_analyze_document_from_url: {e}")
            raise ValueError(f"Error: {traceback.format_exc()}. Error: {e}")
        finally:
            logger.info("Method begin_analyze_document_from_url ended")

    @staticmethod
    def _field_to_text(field) -> str:
        """Coerce a DocumentField (or its value) into a plain, JSON-serializable string.

        Object/collection contract fields (e.g. Parties, Addresses) expose nested
        DocumentField objects via ``.value``, which are not JSON serializable. Prefer
        a string ``.value``; for object fields whose value is a dict of sub-fields,
        prefer a ``Name`` sub-field, then the field's raw ``.content`` span, then
        ``str()`` as a last resort.
        """
        if field is None:
            return ""
        value = getattr(field, "value", None)
        if isinstance(value, str):
            return value
        # Object fields (e.g. a party) carry a dict of named sub-fields.
        if isinstance(value, dict):
            for key in ("Name", "name"):
                if value.get(key) is not None:
                    return AzureFormRecognizerClient._field_to_text(value[key])
            content = getattr(field, "content", None)
            if content:
                return content
            # No name/content: join the readable text of the sub-fields.
            parts = [
                AzureFormRecognizerClient._field_to_text(sub) for sub in value.values()
            ]
            return "; ".join(p for p in parts if p)
        content = getattr(field, "content", None)
        if content:
            return content
        if value is not None and not hasattr(value, "value"):
            return str(value)
        return str(field)

    def begin_analyze_contract_from_url(self, source_url: str):
        """
        Analyze a contract document using the prebuilt-contract model.

        The prebuilt-contract model extracts contract-specific entities including:
        - Parties: Entities entering into the contract
        - Contract type: NDA, employment agreement, lease, etc.
        - Key dates: Effective date, expiration, renewal dates
        - Clauses: Payment terms, termination conditions, liability, etc.
        - Monetary amounts: Values, prices, payments
        - Addresses: Physical locations referenced in the contract

        Args:
            source_url: URL of the contract document to analyze

        Returns:
            dict: Contract content and extracted entities in a structured format:
                {
                    "content": str,  # Full text content of the contract
                    "contract_type": str,
                    "parties": list[str],
                    "effective_date": str,
                    "expiration_date": str,
                    "clauses": dict,
                    "monetary_amounts": list[dict],
                    "addresses": list[str]
                }
        """
        model_id = "prebuilt-contract"

        try:
            logger.info("Method begin_analyze_contract_from_url started")
            logger.info("Model ID selected: %s", model_id)

            poller = self.document_analysis_client.begin_analyze_document_from_url(
                model_id, document_url=source_url
            )
            contract_results = poller.result()

            # Extract full text content
            content = contract_results.content if contract_results.content else ""

            # Extract contract-specific fields
            contract_data = {
                "content": content,
                "contract_type": None,
                "parties": [],
                "effective_date": None,
                "expiration_date": None,
                "clauses": {},
                "monetary_amounts": [],
                "addresses": [],
            }

            # Extract fields from the contract analysis
            if hasattr(contract_results, "documents") and contract_results.documents:
                document = contract_results.documents[0]
                fields = document.fields if hasattr(document, "fields") else {}

                # Extract contract type
                if "ContractType" in fields and fields["ContractType"]:
                    contract_data["contract_type"] = self._field_to_text(
                        fields["ContractType"]
                    )

                # Extract parties
                if "Parties" in fields and fields["Parties"]:
                    parties_field = fields["Parties"]
                    if hasattr(parties_field, "value") and isinstance(
                        parties_field.value, list
                    ):
                        contract_data["parties"] = [
                            self._field_to_text(party) for party in parties_field.value
                        ]

                # Extract dates
                if "EffectiveDate" in fields and fields["EffectiveDate"]:
                    contract_data["effective_date"] = str(fields["EffectiveDate"].value)

                if "ExpirationDate" in fields and fields["ExpirationDate"]:
                    contract_data["expiration_date"] = str(
                        fields["ExpirationDate"].value
                    )

                # Extract monetary amounts
                if "MonetaryAmounts" in fields and fields["MonetaryAmounts"]:
                    amounts_field = fields["MonetaryAmounts"]
                    if hasattr(amounts_field, "value") and isinstance(
                        amounts_field.value, list
                    ):
                        contract_data["monetary_amounts"] = [
                            {
                                "amount": (
                                    str(amt.value)
                                    if hasattr(amt, "value")
                                    else str(amt)
                                )
                            }
                            for amt in amounts_field.value
                        ]

                # Extract addresses
                if "Addresses" in fields and fields["Addresses"]:
                    addresses_field = fields["Addresses"]
                    if hasattr(addresses_field, "value") and isinstance(
                        addresses_field.value, list
                    ):
                        contract_data["addresses"] = [
                            self._field_to_text(addr) for addr in addresses_field.value
                        ]

                # Extract key clauses
                clause_fields = [
                    "PaymentTerms",
                    "TerminationClause",
                    "LiabilityClause",
                    "ConfidentialityClause",
                    "IndemnificationClause",
                ]
                for clause_name in clause_fields:
                    if clause_name in fields and fields[clause_name]:
                        contract_data["clauses"][clause_name] = str(
                            fields[clause_name].value
                        )

            logger.info("Extracted contract type: %s", contract_data["contract_type"])
            logger.info("Extracted %d parties", len(contract_data["parties"]))

            return contract_data

        except Exception as e:
            logger.exception("Exception in begin_analyze_contract_from_url: %s", e)
            raise ValueError(
                f"Error analyzing contract: {traceback.format_exc()}. Error: {e}"
            )
        finally:
            logger.info("Method begin_analyze_contract_from_url ended")
