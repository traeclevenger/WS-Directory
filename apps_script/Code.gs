// WS Directory — Google Apps Script backend
// Deploy as: Web app | Execute as: Me | Who has access: Anyone
//
// Before deploying, add your Anthropic API key:
//   Apps Script → Project Settings → Script Properties
//   Add property: ANTHROPIC_API_KEY = sk-ant-...

const CLAUDE_MODEL = "claude-haiku-4-5";

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const query = (body.query || "").trim();
    const families = body.families || [];

    if (!query) return respond({ error: "No query provided." });
    if (!families.length) return respond({ error: "No families provided." });

    const catalogueText = families
      .map(f => `${f.name}: ${f.desc || "(no description)"}`)
      .join("\n");

    const systemPrompt =
      "You are a search assistant for a church family directory. " +
      "The user will describe a person's physical appearance. " +
      "Your job is to find which families in the directory best match that description. " +
      "Each entry in the directory is in the format: Family Name: description of the people in their photo.\n\n" +
      "Return ONLY a JSON array of matching family name strings, ranked by relevance (best match first). " +
      "Be selective — only include families that are a genuinely good match. " +
      "If nothing matches well, return an empty array []. " +
      "Return only the JSON array — no explanation, no other text.\n\n" +
      "## Family directory\n" + catalogueText;

    const apiKey = PropertiesService.getScriptProperties().getProperty("ANTHROPIC_API_KEY");
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set in Script Properties.");

    const response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
      method: "post",
      contentType: "application/json",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      payload: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: 512,
        system: systemPrompt,
        messages: [{ role: "user", content: query }],
      }),
      muteHttpExceptions: true,
    });

    const result = JSON.parse(response.getContentText());
    if (result.error) throw new Error(result.error.message);

    const rawText = result.content[0].text.trim();
    let matches = [];
    try {
      const jsonMatch = rawText.match(/\[[\s\S]*\]/);
      if (jsonMatch) matches = JSON.parse(jsonMatch[0]);
    } catch (parseErr) { /* return empty matches on parse failure */ }

    return respond({ matches });

  } catch (err) {
    return respond({ error: err.message });
  }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

// Run this in the Apps Script editor to verify your setup
function testPost() {
  const result = doPost({
    postData: {
      contents: JSON.stringify({
        query: "older woman with short gray hair and glasses",
        families: [
          { name: "Smith, John & Mary", desc: "A woman in her late 60s with short gray hair and glasses. A man in his 70s with white hair." },
          { name: "Johnson, Bob & Sue", desc: "A man in his 40s with dark brown hair and a beard." },
        ]
      })
    }
  });
  Logger.log(result.getContent());
}
