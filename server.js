const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const { runUnderwritingGraph } = require("./lib/underwritingGraph");

const ROOT = __dirname;
const PUBLIC_DIR = path.join(ROOT, "public");
const DATA_DIR = path.join(ROOT, "data", "submissions");
const CHAT_HISTORY_DIR = path.join(ROOT, "data", "chat_history");
const GUIDE_DIR = path.join(ROOT, "data", "guide");
const SEARCH_METADATA_PATH = path.join(ROOT, "data", "metadata.json");
const PORT = Number(process.env.PORT || 3000);

loadEnv(path.join(ROOT, ".env"));

const OPENAI_API_KEY = normalizeEnvSecret(process.env.OPENAI_API_KEY);
const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-5.4-nano";

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".pdf": "application/pdf",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon"
};

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "GET" && req.url === "/health") {
      return sendJson(res, 200, { ok: true, model: OPENAI_MODEL });
    }

    if (req.method === "POST" && req.url === "/api/chat") {
      return handleChat(req, res);
    }

    if (req.method === "POST" && req.url.startsWith("/api/submissions/") && req.url.endsWith("/chat-history")) {
      return handleChatHistorySave(req, res);
    }

    if (req.method === "GET" && req.url.startsWith("/api/submissions/") && req.url.endsWith("/guides")) {
      return handleGuideList(req, res);
    }

    if (req.method === "PUT" && req.url.startsWith("/api/submissions/") && req.url.endsWith("/guides")) {
      return handleGuideSave(req, res);
    }

    if (req.method === "GET" && req.url === "/api/submissions") {
      return handleSubmissionsList(res);
    }

    if (req.method === "GET" && req.url === "/api/search-metadata") {
      return handleSearchMetadata(res);
    }

    if (req.method === "GET" && req.url.startsWith("/api/submissions/") && req.url.includes("/files/")) {
      return handleSubmissionFile(req, res);
    }

    if (req.method === "GET" && req.url.startsWith("/api/submissions/") && req.url.endsWith("/chat-history")) {
      return handleChatHistoryList(req, res);
    }

    if (req.method === "GET" && req.url.startsWith("/api/submissions/") && req.url.includes("/chat-history/")) {
      return handleChatHistoryDetail(req, res);
    }

    if (req.method === "GET" && req.url.startsWith("/api/submissions/")) {
      return handleSubmissionDetail(req, res);
    }

    if (req.method === "GET") {
      return serveStatic(req, res);
    }

    sendJson(res, 405, { error: "Method not allowed" });
  } catch (error) {
    console.error(error);
    sendJson(res, 500, { error: "Unexpected server error" });
  }
});

server.listen(PORT, () => {
  console.log(`Agentic underwriting chat is running at http://localhost:${PORT}`);
  console.log(`Using model: ${OPENAI_MODEL}`);
});

function handleSubmissionsList(res) {
  if (!fs.existsSync(DATA_DIR)) {
    return sendJson(res, 200, { submissions: [] });
  }

  const submissions = fs
    .readdirSync(DATA_DIR)
    .filter((entryName) => {
      const metadataPath = path.join(DATA_DIR, entryName, "metadata.json");
      return fs.existsSync(metadataPath);
    })
    .sort()
    .map((folderName) => {
      const metadataPath = path.join(DATA_DIR, folderName, "metadata.json");
      const submission = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
      const coverage = submission.coverage || {};
      const applicant = submission.applicant || {};

      return {
        id: folderName,
        submission_id: submission.id || folderName,
        title: submission.title || folderName,
        insured: applicant.insured_name || "Unknown insured",
        coverage: Array.isArray(coverage.lines_requested)
          ? coverage.lines_requested.join(", ")
          : "Coverage TBD",
        status: submission.status || "New",
        received_at: submission.received_at || null,
        file_created_at: submission.file_created_at || null
      };
    });

  sendJson(res, 200, { submissions });
}

function handleSearchMetadata(res) {
  if (!fs.existsSync(SEARCH_METADATA_PATH)) {
    return sendJson(res, 200, { submissions: [] });
  }

  sendJson(res, 200, JSON.parse(fs.readFileSync(SEARCH_METADATA_PATH, "utf8")));
}

function handleSubmissionDetail(req, res) {
  const id = decodeURIComponent(req.url.replace("/api/submissions/", "").split("?")[0]);

  if (!/^[a-zA-Z0-9._-]+$/.test(id)) {
    return sendJson(res, 400, { error: "Invalid submission id." });
  }

  const folderPath = path.normalize(path.join(DATA_DIR, id));
  const metadataPath = path.join(folderPath, "metadata.json");

  if (!folderPath.startsWith(DATA_DIR) || !fs.existsSync(metadataPath)) {
    return sendJson(res, 404, { error: "Submission not found." });
  }

  const submission = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
  const documents = (submission.documents || []).map((document) => {
    const documentPath = path.normalize(path.join(folderPath, document.file_name));
    const isTextFile = /\.(txt|md|csv)$/i.test(document.file_name);
    const isPdfFile = /\.pdf$/i.test(document.file_name);
    const content =
      isTextFile && documentPath.startsWith(folderPath) && fs.existsSync(documentPath)
        ? fs.readFileSync(documentPath, "utf8")
        : isPdfFile && documentPath.startsWith(folderPath) && fs.existsSync(documentPath)
          ? extractSimplePdfText(documentPath)
        : "";

    return {
      ...document,
      url: `/api/submissions/${encodeURIComponent(id)}/files/${encodeURIComponent(document.file_name)}`,
      content
    };
  });

  sendJson(res, 200, {
    id,
    submission: {
      ...submission,
      documents
    }
  });
}

function handleSubmissionFile(req, res) {
  const parts = req.url.split("?")[0].split("/files/");
  const id = decodeURIComponent(parts[0].replace("/api/submissions/", ""));
  const fileName = decodeURIComponent(parts[1] || "");

  if (!/^[a-zA-Z0-9._-]+$/.test(id) || !/^[a-zA-Z0-9._-]+$/.test(fileName)) {
    return sendText(res, 400, "Invalid file request");
  }

  const folderPath = path.normalize(path.join(DATA_DIR, id));
  const filePath = path.normalize(path.join(folderPath, fileName));

  if (!folderPath.startsWith(DATA_DIR) || !filePath.startsWith(folderPath) || !fs.existsSync(filePath)) {
    return sendText(res, 404, "File not found");
  }

  const ext = path.extname(filePath);
  res.writeHead(200, {
    "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
    "Content-Disposition": `inline; filename="${fileName}"`,
    "Cache-Control": "no-store"
  });
  fs.createReadStream(filePath).pipe(res);
}

function handleChatHistoryList(req, res) {
  const id = decodeURIComponent(
    req.url.replace("/api/submissions/", "").replace("/chat-history", "").split("?")[0]
  );

  if (!/^[a-zA-Z0-9._-]+$/.test(id)) {
    return sendJson(res, 400, { error: "Invalid submission id." });
  }

  const historyPath = path.normalize(path.join(CHAT_HISTORY_DIR, id));

  if (!historyPath.startsWith(CHAT_HISTORY_DIR) || !fs.existsSync(historyPath)) {
    return sendJson(res, 200, { chat_history: [] });
  }

  const chatHistory = fs
    .readdirSync(historyPath)
    .filter((fileName) => /\.json$/i.test(fileName))
    .sort()
    .map((fileName) => {
      const record = JSON.parse(fs.readFileSync(path.join(historyPath, fileName), "utf8"));
      return {
        id: record.id || fileName.replace(/\.json$/i, ""),
        title: record.title || fileName,
        created_at: record.created_at || null,
        updated_at: record.updated_at || null,
        message_count: Array.isArray(record.messages) ? record.messages.length : 0
      };
    });

  sendJson(res, 200, { chat_history: chatHistory });
}

function handleChatHistoryDetail(req, res) {
  const parts = req.url.split("?")[0].split("/chat-history/");
  const id = decodeURIComponent(parts[0].replace("/api/submissions/", ""));
  const historyId = decodeURIComponent(parts[1] || "");

  if (!/^[a-zA-Z0-9._-]+$/.test(id) || !/^[a-zA-Z0-9._-]+$/.test(historyId)) {
    return sendJson(res, 400, { error: "Invalid chat history request." });
  }

  const historyPath = path.normalize(path.join(CHAT_HISTORY_DIR, id));

  if (!historyPath.startsWith(CHAT_HISTORY_DIR) || !fs.existsSync(historyPath)) {
    return sendJson(res, 404, { error: "Chat history not found." });
  }

  const match = fs
    .readdirSync(historyPath)
    .find((fileName) => {
      if (!/\.json$/i.test(fileName)) {
        return false;
      }

      const record = JSON.parse(fs.readFileSync(path.join(historyPath, fileName), "utf8"));
      return record.id === historyId || fileName.replace(/\.json$/i, "") === historyId;
    });

  if (!match) {
    return sendJson(res, 404, { error: "Chat history not found." });
  }

  const record = JSON.parse(fs.readFileSync(path.join(historyPath, match), "utf8"));
  sendJson(res, 200, { chat_history: record });
}

async function handleChatHistorySave(req, res) {
  const id = decodeURIComponent(
    req.url.replace("/api/submissions/", "").replace("/chat-history", "").split("?")[0]
  );

  if (!/^[a-zA-Z0-9._-]+$/.test(id)) {
    return sendJson(res, 400, { error: "Invalid submission id." });
  }

  const body = await readJson(req);
  const messages = Array.isArray(body.messages) ? body.messages : [];

  if (!messages.length) {
    return sendJson(res, 400, { error: "No chat messages were provided." });
  }

  const historyPath = path.normalize(path.join(CHAT_HISTORY_DIR, id));
  if (!historyPath.startsWith(CHAT_HISTORY_DIR)) {
    return sendJson(res, 400, { error: "Invalid chat history path." });
  }

  fs.mkdirSync(historyPath, { recursive: true });

  const now = new Date().toISOString();
  const existingId = typeof body.history_id === "string" ? body.history_id : "";
  const existingFile = existingId ? findChatHistoryFile(historyPath, existingId) : null;
  const firstUserMessage = messages.find((message) => message.role === "user");
  const title = body.title || makeChatTitle(firstUserMessage ? firstUserMessage.content : "New chat");
  const historyId = existingId || `${id}-chat-${Date.now()}`;
  const fileName = existingFile || `${slugify(historyId)}.json`;
  const filePath = path.join(historyPath, fileName);
  const existingRecord = fs.existsSync(filePath) ? JSON.parse(fs.readFileSync(filePath, "utf8")) : {};

  const record = {
    id: existingRecord.id || historyId,
    title: existingRecord.title || title,
    created_at: existingRecord.created_at || now,
    updated_at: now,
    messages: messages.map((message) => ({
      role: message.role === "assistant" ? "assistant" : "user",
      content: String(message.content || "")
    }))
  };

  fs.writeFileSync(filePath, `${JSON.stringify(record, null, 2)}\n`);
  sendJson(res, 200, { chat_history: record });
}

function handleGuideList(req, res) {
  const id = decodeURIComponent(
    req.url.replace("/api/submissions/", "").replace("/guides", "").split("?")[0]
  );

  if (!isValidSubmissionId(id)) {
    return sendJson(res, 400, { error: "Invalid submission id." });
  }

  if (!submissionExists(id)) {
    return sendJson(res, 404, { error: "Submission not found." });
  }

  const guideRecord = readGuideRecord(id);
  sendJson(res, 200, { guide: guideRecord });
}

async function handleGuideSave(req, res) {
  const id = decodeURIComponent(
    req.url.replace("/api/submissions/", "").replace("/guides", "").split("?")[0]
  );

  if (!isValidSubmissionId(id)) {
    return sendJson(res, 400, { error: "Invalid submission id." });
  }

  if (!submissionExists(id)) {
    return sendJson(res, 404, { error: "Submission not found." });
  }

  const body = await readJson(req);
  const previousRecord = readGuideRecord(id);
  const now = new Date().toISOString();
  const guides = sanitizeGuides(body.guides, previousRecord.guides || [], now);
  const guideRecord = {
    submission_id: id,
    updated_at: now,
    guides
  };
  const guidePath = getGuidePath(id);

  fs.mkdirSync(GUIDE_DIR, { recursive: true });
  fs.writeFileSync(guidePath, `${JSON.stringify(guideRecord, null, 2)}\n`);

  sendJson(res, 200, { guide: guideRecord });
}

function readGuideRecord(id) {
  const guidePath = getGuidePath(id);

  if (!guidePath || !fs.existsSync(guidePath)) {
    return {
      submission_id: id,
      updated_at: null,
      guides: []
    };
  }

  const record = JSON.parse(fs.readFileSync(guidePath, "utf8"));
  const now = new Date().toISOString();
  return {
    submission_id: record.submission_id || id,
    updated_at: record.updated_at || null,
    guides: sanitizeGuides(record.guides, [], now, false)
  };
}

function sanitizeGuides(guides, previousGuides, now, refreshUpdatedAt = true) {
  if (!Array.isArray(guides)) {
    return [];
  }

  const previousById = new Map(
    previousGuides
      .filter((guide) => guide && guide.id)
      .map((guide) => [guide.id, guide])
  );

  return guides
    .map((guide, index) => {
      const guideObject = typeof guide === "string" ? { text: guide } : guide || {};
      const text = String(guideObject.text || "").trim();

      if (!text) {
        return null;
      }

      const rawId = String(guideObject.id || "").trim();
      const id = /^[a-zA-Z0-9._-]+$/.test(rawId) ? rawId : `guide-${Date.now()}-${index}`;
      const previous = previousById.get(id);

      return {
        id,
        text,
        created_at: guideObject.created_at || (previous && previous.created_at) || now,
        updated_at: refreshUpdatedAt ? now : guideObject.updated_at || (previous && previous.updated_at) || now
      };
    })
    .filter(Boolean);
}

function getGuidePath(id) {
  const guidePath = path.normalize(path.join(GUIDE_DIR, `${id}.json`));
  return guidePath.startsWith(GUIDE_DIR) ? guidePath : null;
}

function isValidSubmissionId(id) {
  return /^[a-zA-Z0-9._-]+$/.test(id);
}

function submissionExists(id) {
  return fs.existsSync(path.join(DATA_DIR, id, "metadata.json"));
}

function findChatHistoryFile(historyPath, historyId) {
  if (!fs.existsSync(historyPath)) {
    return null;
  }

  return (
    fs
      .readdirSync(historyPath)
      .find((fileName) => {
        if (!/\.json$/i.test(fileName)) {
          return false;
        }

        const record = JSON.parse(fs.readFileSync(path.join(historyPath, fileName), "utf8"));
        return record.id === historyId || fileName.replace(/\.json$/i, "") === historyId;
      }) || null
  );
}

function makeChatTitle(content) {
  const normalized = String(content || "New chat").replace(/\s+/g, " ").trim();
  return normalized.length > 48 ? `${normalized.slice(0, 45)}...` : normalized || "New chat";
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

async function handleChat(req, res) {
  if (!OPENAI_API_KEY || OPENAI_API_KEY === "replace_with_your_openai_api_key") {
    return sendJson(res, 400, {
      error: "Missing OPENAI_API_KEY. Add your key to .env, then restart the server."
    });
  }

  const body = await readJson(req);
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const guideInstructions = Array.isArray(body.guides)
    ? body.guides.map((guide) => String(guide || "").trim()).filter(Boolean)
    : [];

  if (!messages.length) {
    return sendJson(res, 400, { error: "No messages were provided." });
  }

  const input = messages.map((message) => ({
    role: message.role === "assistant" ? "assistant" : "user",
    content: String(message.content || "")
  }));

  try {
    const graphResult = await runUnderwritingGraph({
      messages: input,
      model: OPENAI_MODEL,
      apiKey: OPENAI_API_KEY,
      guideInstructions,
      callOpenAI: callOpenAIResponses
    });

    sendJson(res, 200, {
      reply: graphResult.reply,
      model: OPENAI_MODEL,
      id: graphResult.responseId || null,
      framework: "langgraph"
    });
  } catch (error) {
    const message = error && error.message ? error.message : "OpenAI request failed";
    const invalidKeyMessage = message.toLowerCase().includes("incorrect api key")
      ? `${message} The local server is using the key loaded at startup. Replace OPENAI_API_KEY in .env with a newly generated key, then restart the server.`
      : message;
    sendJson(res, 502, { error: invalidKeyMessage });
  }
}

async function callOpenAIResponses({ apiKey, model, messages, guideInstructions }) {
  const payload = {
    model,
    instructions: buildModelInstructions(guideInstructions),
    input: messages,
    max_output_tokens: 900
  };

  const openaiResponse = await postJson("api.openai.com", "/v1/responses", payload, {
    Authorization: `Bearer ${apiKey}`
  });

  return {
    reply: extractOutputText(openaiResponse),
    id: openaiResponse.id || null
  };
}

function buildModelInstructions(guideInstructions) {
  const baseInstructions = [
    "You are an underwriting copilot for cyber insurance workflows.",
    "Help evaluate submissions, ask for missing information, summarize risks, and explain your reasoning.",
    "Do not make binding coverage or pricing decisions. Flag uncertainty and recommend human review for high-impact decisions.",
    "Keep answers concise, practical, and structured for a cyber underwriter."
  ];

  const guides = Array.isArray(guideInstructions)
    ? guideInstructions.map((guide) => String(guide || "").trim()).filter(Boolean)
    : [];

  if (!guides.length) {
    return baseInstructions.join(" ");
  }

  return [
    baseInstructions.join(" "),
    "",
    "Additional underwriting guide instructions. Treat these as higher-priority operating guidance for this request:",
    ...guides.map((guide, index) => `${index + 1}. ${guide}`)
  ].join("\n");
}

function serveStatic(req, res) {
  const urlPath = req.url === "/" ? "/index.html" : req.url.split("?")[0];
  const decodedPath = decodeURIComponent(urlPath);
  const filePath = path.normalize(path.join(PUBLIC_DIR, decodedPath));

  if (!filePath.startsWith(PUBLIC_DIR)) {
    return sendText(res, 403, "Forbidden");
  }

  fs.readFile(filePath, (error, data) => {
    if (error) {
      return sendText(res, 404, "Not found");
    }

    const ext = path.extname(filePath);
    res.writeHead(200, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Cache-Control": "no-store"
    });
    res.end(data);
  });
}

function postJson(hostname, requestPath, payload, headers) {
  const body = JSON.stringify(payload);

  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname,
        path: requestPath,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
          ...headers
        }
      },
      (res) => {
        let data = "";

        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          data += chunk;
        });
        res.on("end", () => {
          let parsed;
          try {
            parsed = data ? JSON.parse(data) : {};
          } catch (error) {
            return reject(new Error(`OpenAI returned a non-JSON response (${res.statusCode}).`));
          }

          if (res.statusCode < 200 || res.statusCode >= 300) {
            const apiMessage = parsed.error && parsed.error.message ? parsed.error.message : data;
            return reject(new Error(apiMessage || `OpenAI request failed with ${res.statusCode}.`));
          }

          resolve(parsed);
        });
      }
    );

    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

function extractOutputText(response) {
  if (typeof response.output_text === "string" && response.output_text.trim()) {
    return response.output_text;
  }

  const chunks = [];
  const output = Array.isArray(response.output) ? response.output : [];

  output.forEach((item) => {
    const content = Array.isArray(item.content) ? item.content : [];
    content.forEach((part) => {
      if (typeof part.text === "string") {
        chunks.push(part.text);
      }
    });
  });

  return chunks.join("\n").trim() || "I could not produce a response.";
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let data = "";

    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 1_000_000) {
        req.destroy();
        reject(new Error("Request body is too large."));
      }
    });

    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (error) {
        reject(new Error("Invalid JSON body."));
      }
    });

    req.on("error", reject);
  });
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body)
  });
  res.end(body);
}

function sendText(res, statusCode, text) {
  res.writeHead(statusCode, { "Content-Type": "text/plain; charset=utf-8" });
  res.end(text);
}

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      return;
    }

    const equalsIndex = trimmed.indexOf("=");
    if (equalsIndex === -1) {
      return;
    }

    const key = trimmed.slice(0, equalsIndex).trim();
    let value = trimmed.slice(equalsIndex + 1).trim();

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (!process.env[key]) {
      process.env[key] = value;
    }
  });
}

function normalizeEnvSecret(value) {
  if (!value) {
    return "";
  }

  const trimmed = String(value).trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1).trim();
  }

  return trimmed;
}

function extractSimplePdfText(filePath) {
  const pdf = fs.readFileSync(filePath, "latin1");
  const matches = [...pdf.matchAll(/\((.*?)\)\s*Tj/g)];

  return matches
    .map((match) =>
      match[1]
        .replace(/\\\(/g, "(")
        .replace(/\\\)/g, ")")
        .replace(/\\\\/g, "\\")
    )
    .join("\n")
    .trim();
}
