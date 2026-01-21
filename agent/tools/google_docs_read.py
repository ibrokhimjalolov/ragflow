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


class GoogleDocsReadParam(ToolParamBase):
    """
    Define the Google Docs Read component parameters.
    """

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "google_docs_read",
            "description": """Read content from a Google Doc by document ID.
The document_id can be found in the Google Doc URL: https://docs.google.com/document/d/{document_id}/edit
Returns the full document JSON structure including body content, styles, and element indices for precise editing.""",
            "parameters": {
                "document_id": {
                    "type": "string",
                    "description": "The Google Doc document ID (extracted from the document URL)",
                    "default": "{sys.query}",
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
            }
        }


class GoogleDocsRead(ToolBase, ABC):
    component_name = "GoogleDocsRead"

    def _get_docs_service(self):
        """Build and return Google Docs API service using service account."""
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]

        service_account_info = json.loads(self._param.service_account_json)
        creds = ServiceAccountCredentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        return build("docs", "v1", credentials=creds)

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("GoogleDocsRead processing"):
            return

        document_id = kwargs.get("document_id", "").strip()

        if not document_id:
            self.set_output("_ERROR", "document_id is required")
            self.set_output("success", False)
            return "Error: document_id is required"

        last_e = ""
        for _ in range(self._param.max_retries + 1):
            if self.check_if_canceled("GoogleDocsRead processing"):
                return

            try:
                service = self._get_docs_service()
                # Get full document JSON
                document = service.documents().get(documentId=document_id).execute()

                # Return full document JSON as string for LLM context
                return json.dumps(document, indent=2)

            except Exception as e:
                if self.check_if_canceled("GoogleDocsRead processing"):
                    return

                last_e = str(e)
                logging.exception(f"GoogleDocsRead error: {e}")
                time.sleep(self._param.delay_after_error)

        if last_e:
            self.set_output("_ERROR", last_e)
            self.set_output("success", False)
            return f"GoogleDocsRead error: {last_e}"

        assert False, self.output()

    def thoughts(self) -> str:
        inputs = self.get_input()
        doc_id = inputs.get("document_id", "")
        return f"Reading Google Doc: {doc_id[:30]}..." if doc_id else "Reading Google Doc..."
