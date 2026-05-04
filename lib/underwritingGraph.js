async function runUnderwritingGraph({ messages, model, apiKey, guideInstructions, callOpenAI }) {
  ensureWebStreamGlobals();

  const { Annotation, END, START, StateGraph } = await import("@langchain/langgraph");

  const GraphState = Annotation.Root({
    messages: Annotation({
      reducer: (_left, right) => right,
      default: () => []
    }),
    model: Annotation({
      reducer: (_left, right) => right,
      default: () => model
    }),
    apiKey: Annotation({
      reducer: (_left, right) => right,
      default: () => apiKey
    }),
    guideInstructions: Annotation({
      reducer: (_left, right) => right,
      default: () => []
    }),
    reply: Annotation({
      reducer: (_left, right) => right,
      default: () => ""
    }),
    responseId: Annotation({
      reducer: (_left, right) => right,
      default: () => null
    })
  });

  async function callUnderwritingModel(state) {
    const response = await callOpenAI({
      apiKey: state.apiKey,
      guideInstructions: state.guideInstructions,
      model: state.model,
      messages: state.messages
    });

    return {
      reply: response.reply,
      responseId: response.id
    };
  }

  const graph = new StateGraph(GraphState)
    .addNode("underwriting_model", callUnderwritingModel)
    .addEdge(START, "underwriting_model")
    .addEdge("underwriting_model", END)
    .compile();

  return graph.invoke({
    messages,
    model,
    apiKey,
    guideInstructions
  });
}

function ensureWebStreamGlobals() {
  if (
    typeof AbortSignal !== "undefined" &&
    AbortSignal.prototype &&
    typeof AbortSignal.prototype.throwIfAborted !== "function"
  ) {
    AbortSignal.prototype.throwIfAborted = function throwIfAborted() {
      if (this.aborted) {
        throw this.reason || new Error("The operation was aborted.");
      }
    };
  }

  if (
    typeof globalThis.ReadableStream !== "undefined" &&
    typeof globalThis.WritableStream !== "undefined" &&
    typeof globalThis.TransformStream !== "undefined"
  ) {
    return;
  }

  const {
    ReadableStream,
    TransformStream,
    WritableStream
  } = require("stream/web");

  globalThis.ReadableStream = globalThis.ReadableStream || ReadableStream;
  globalThis.TransformStream = globalThis.TransformStream || TransformStream;
  globalThis.WritableStream = globalThis.WritableStream || WritableStream;
}

module.exports = {
  runUnderwritingGraph
};
