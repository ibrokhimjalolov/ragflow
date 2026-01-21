#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import json
import logging
import os
import time
from abc import ABC

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout


class GoogleDocsWriteParam(ToolParamBase):
    """
    Define the Google Docs Write component parameters.
    """

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "google_docs_write",
            "description": """Write/update content in a Google Doc by document ID using batchUpdate operations.
The document_id can be found in the Google Doc URL: https://docs.google.com/document/d/{document_id}/edit
The operations parameter accepts a JSON array of Google Docs API requests such as insertText, deleteContentRange, replaceAllText, etc.
Example operations:
[
    {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": 10}}},
    {"insertText": {"location": {"index": 1}, "text": "Hello World"}}
]
Returns the response from the batchUpdate API call.""",
            "parameters": {
                "document_id": {
                    "type": "string",
                    "description": "The Google Doc document ID (extracted from the document URL)",
                    "default": "",
                    "required": True
                },
                "operations": {
                    "type": "string",
                    "description": "JSON array of Google Docs API batchUpdate requests",
                    "default": "",
                    "required": True
                }
            }
        }
        super().__init__()
        # Service account JSON key - configured by user when adding tool to agent
        self.service_account_json = ""

    def check(self):
        self.check_empty(self.service_account_json, "Service Account JSON")

    def get_input_form(self) -> dict[str, dict]:
        return {
            "document_id": {
                "name": "Document ID",
                "type": "line"
            },
            "operations": {
                "name": "Operations (JSON)",
                "type": "paragraph"
            }
        }


class GoogleDocsWrite(ToolBase, ABC):
    component_name = "GoogleDocsWrite"

    def _get_docs_service(self):
        """Build and return Google Docs API service using service account."""
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive"
        ]

        service_account_info = json.loads(self._param.service_account_json)
        creds = ServiceAccountCredentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        return build("docs", "v1", credentials=creds)

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("GoogleDocsWrite processing"):
            return

        document_id = kwargs.get("document_id", "").strip()
        operations_str = kwargs.get("operations", "").strip()

        if not document_id:
            self.set_output("_ERROR", "document_id is required")
            self.set_output("success", False)
            return "Error: document_id is required"

        if not operations_str:
            self.set_output("_ERROR", "operations is required")
            self.set_output("success", False)
            return "Error: operations is required"

        try:
            operations = json.loads(operations_str)
            if not isinstance(operations, list):
                self.set_output("_ERROR", "operations must be a JSON array")
                self.set_output("success", False)
                return "Error: operations must be a JSON array"
        except json.JSONDecodeError as e:
            self.set_output("_ERROR", f"Invalid JSON in operations: {e}")
            self.set_output("success", False)
            return f"Error: Invalid JSON in operations: {e}"

        last_e = ""
        for _ in range(self._param.max_retries + 1):
            if self.check_if_canceled("GoogleDocsWrite processing"):
                return

            try:
                service = self._get_docs_service()
                # Execute batchUpdate with the provided operations
                result = service.documents().batchUpdate(
                    documentId=document_id,
                    body={"requests": operations}
                ).execute()

                self.set_output("success", True)
                return json.dumps(result, indent=2)

            except Exception as e:
                if self.check_if_canceled("GoogleDocsWrite processing"):
                    return

                last_e = str(e)
                logging.exception(f"GoogleDocsWrite error: {e}")
                time.sleep(self._param.delay_after_error)

        if last_e:
            self.set_output("_ERROR", last_e)
            self.set_output("success", False)
            return f"GoogleDocsWrite error: {last_e}"

        assert False, self.output()

    def thoughts(self) -> str:
        inputs = self.get_input()
        doc_id = inputs.get("document_id", "")
        return f"Writing to Google Doc: {doc_id[:30]}..." if doc_id else "Writing to Google Doc..."
