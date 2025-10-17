# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import logging
from typing import Optional

from pyrit.common import net_utility
from pyrit.models import PromptRequestResponse, construct_response_from_request
from pyrit.prompt_target import PromptTarget, limit_requests_per_minute

logger = logging.getLogger(__name__)

class TockTarget(PromptTarget):
    def __init__(
        self,
        *,
        max_requests_per_minute: Optional[int] = None,
        user_id: str = "demo-user"
    ) -> None:
        super().__init__(max_requests_per_minute=max_requests_per_minute)
        self._endpoint = "http://localhost:8080/io/app/new_assistant/web"
        self._user_id = user_id

    @limit_requests_per_minute
    async def send_prompt_async(self, *, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        self._validate_request(prompt_request=prompt_request)
        request = prompt_request.request_pieces[0]
        logger.info(f"Sending prompt to Tock: {request}")
        response_text = await self._complete_text_async(request.converted_value)
        response_entry = construct_response_from_request(request=request, response_text_pieces=[response_text])
        return response_entry

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        n_pieces = len(prompt_request.request_pieces)
        if n_pieces != 1:
            raise ValueError(f"This target only accepts a single prompt piece. Received: {n_pieces}.")
        piece_type = prompt_request.request_pieces[0].converted_value_data_type
        if piece_type != "text":
            raise ValueError(f"This target only accepts text. Received: {piece_type}.")

    async def _complete_text_async(self, text: str) -> str:
        payload = {
            "query": text,
            "userId": self._user_id
        }
        resp = await net_utility.make_request_and_raise_if_error_async(
            endpoint_uri=self._endpoint, method="POST", request_body=payload, post_type="json"
        )
        if not resp.text:
            raise ValueError("Tock response is empty.")
        try:
            json_response = json.loads(resp.text)
            answer = json_response["responses"][0]["text"]
        except Exception as e:
            logger.error(f"Error parsing Tock response: {e}")
            raise ValueError("Invalid Tock response.")
        logger.info(f"Response received from Tock: {answer}")
        return answer
