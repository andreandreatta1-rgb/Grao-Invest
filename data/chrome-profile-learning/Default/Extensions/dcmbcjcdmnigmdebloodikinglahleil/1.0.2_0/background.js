import { CHATGPT_HEADERS, RESOURCE_TYPES, RULE_IDS } from "./constants.js";
import { BROWSER, BrowserType, browserAPI } from "./utils.js";

console.log("Browser: ", BROWSER);
console.log("Platform Type: ", browserAPI.platform);

const MODIFY_HEADER_RULE_ID = RULE_IDS.MODIFY_HEADER_RULE_ID;
const BLOCK_RULE_ID = RULE_IDS.BLOCK_RULE_ID;

const MODIFY_HEADER_RULE = {
  id: MODIFY_HEADER_RULE_ID,
  priority: 1,
  action: {
    type: "modifyHeaders",
    requestHeaders: [
      {
        header: CHATGPT_HEADERS.NAME,
        operation: "set",
        value: CHATGPT_HEADERS.VALUE
      }
    ]
  },
  condition: {
    requestDomains: [CHATGPT_HEADERS.HOST],
    resourceTypes: RESOURCE_TYPES
  }
};

const BLOCK_RULE = {
  id: BLOCK_RULE_ID,
  priority: 1,
  action: { type: "block" },
  condition: {
    urlFilter: `https://${CHATGPT_HEADERS.HOST}/backend-anon/*`,
    resourceTypes: RESOURCE_TYPES
  }
};

export function addChatGptBlockRules() {
  const isSafari = BrowserType.SAFARI === BROWSER;
  const ruleToApply = isSafari ? BLOCK_RULE : MODIFY_HEADER_RULE;
  const ruleToRemove = isSafari ? BLOCK_RULE_ID : MODIFY_HEADER_RULE_ID;

  browserAPI.declarativeNetRequest.updateDynamicRules(
    {
      removeRuleIds: [ruleToRemove],
      addRules: [ruleToApply]
    },
    () => {
      if (browserAPI.runtime.lastError) {
        console.log(
          "ERROR updating rule:",
          browserAPI.runtime.lastError.message
        );
      } else {
        console.log("rule updated successfully");
      }
    }
  );
}

function registerListeners() {
  browserAPI.runtime.onInstalled.addListener(addChatGptBlockRules);
  browserAPI.runtime.onStartup.addListener(addChatGptBlockRules);
}

registerListeners();
