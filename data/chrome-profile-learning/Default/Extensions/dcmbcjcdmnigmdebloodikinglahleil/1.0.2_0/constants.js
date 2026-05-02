import { BROWSER, getRequestResourceTypes } from "./utils.js";

export const CHATGPT_HEADERS = Object.freeze({
  HOST: "chatgpt.com",
  NAME: "ChatGPT-Allowed-Workspace-Id",
  VALUE:
    "7fb09b21-c400-4a68-a7f3-1f94a035df42,c063a5a0-baf3-4b7c-bb4b-2bc3d4a4617f,01868a7a-f72b-447b-943f-74528455078f,5ac326ad-c2c2-437c-bcf3-9368ec1dd33b,1de1b2a7-dbe5-4f8b-8501-1b11481122a0,1baf2450-8bf6-4e8e-a13c-119348bb7f3c"
});

export const RESOURCE_TYPES = Object.freeze(getRequestResourceTypes(BROWSER));

export const RULE_IDS = Object.freeze({
  MODIFY_HEADER_RULE_ID: 1,
  BLOCK_RULE_ID: 2
});
