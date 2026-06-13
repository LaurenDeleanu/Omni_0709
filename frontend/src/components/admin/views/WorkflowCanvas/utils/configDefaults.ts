import { Step } from "@/shared";

export function getDefaultConfig(type: string): string {
  const defaults: Record<string, any> = {
    WELCOME: {
      nextStepId: false,
      cards: [{ id: "welcome-1", type: "TEXT", content: "¡Hola! ¿En qué puedo ayudarte hoy?" }]
    },
    COLLECT_FIELD: {
      nextStepId: false,
      field: "nombre",
      validationType: "none",
      cards: [{ id: "collect-1", type: "TEXT", content: "Por favor, dime tu nombre:" }]
    },
    CHOICE_LIST: {
      nextStepId: false,
      field: "opcion_seleccionada",
      options: ["Sí", "No"],
      cards: [{ id: "choice-1", type: "TEXT", content: "Elige una opción:" }],
      branches: [
        { match: "Sí", goToStepId: "", goToStepOrder: 0 },
        { match: "No", goToStepId: "", goToStepOrder: 0 }
      ]
    },
    FILE_UPLOAD: {
      nextStepId: false,
      field: "documento",
      optional: false,
      acceptType: "any",
      ocrEnabled: false,
      cards: [{ id: "upload-1", type: "TEXT", content: "Por favor, sube tu comprobante o documento:" }]
    },
    SHOW_PRODUCTS: {
      nextStepId: false,
      productIds: [],
      cards: []
    },
    ADD_TO_CART: {
      nextStepId: false,
      cartField: "cart",
      cartSourceField: "seleccion_productos"
    },
    CHECKOUT: {
      nextStepId: false,
      shippingFee: 0,
      gateway: "stripe"
    },
    BOOKING: {
      nextStepId: false,
      field: "fecha_cita",
      scheduleId: "",
      calendarSync: false,
      cards: [{ id: "booking-1", type: "TEXT", content: "Por favor reserva tu cita:" }]
    },
    PAYMENT: {
      nextStepId: false,
      field: "pago_completado",
      amount: 0,
      currency: "USD",
      dynamic: false,
      cards: [{ id: "payment-1", type: "TEXT", content: "Por favor realiza el pago:" }]
    },
    CONDITION: {
      nextStepId: false,
      checkField: "variable_name",
      branches: []
    },
    AB_TEST: {
      nextStepId: false,
      branchAWeight: 50,
      branchAStepId: "",
      branchBStepId: ""
    },
    AI_RESPONDER: {
      nextStepId: false,
      field: "respuesta_ia",
      aiModel: "llama-3.1-8b-instant",
      systemPrompt: "Eres un asistente inteligente de atención al cliente.",
      temperature: 0.7,
      useKnowledgeBase: true,
      cards: []
    },
    AUTONOMOUS_AGENT: {
      nextStepId: false,
      field: "respuesta_ia",
      aiModel: "llama-3.1-8b-instant",
      systemPrompt: "Eres un agente autónomo de ventas con capacidad de enrutamiento.",
      temperature: 0.7,
      useKnowledgeBase: true,
      branches: []
    },
    API_CALL: {
      nextStepId: false,
      apiUrl: "",
      apiMethod: "POST",
      apiHeaders: "{}",
      apiBody: "",
      extractPath: "",
      saveToField: "",
      errorStepId: ""
    },
    CALL_WORKFLOW: {
      nextStepId: false,
      workflowId: ""
    },
    CREATE_LEAD: {
      nextStepId: false,
      field: "leadStage",
      newLeadStage: "qualified"
    },
    HUMAN_TAKEOVER: {
      nextStepId: false,
      prompt: "Un agente humano se conectará pronto."
    },
    COMPLETED: {
      nextStepId: false,
      cards: [{ id: "complete-1", type: "TEXT", content: "¡Muchas gracias! Tu solicitud ha sido completada con éxito. 🎉" }]
    }
  };

  return JSON.stringify(defaults[type] || { nextStepId: false });
}
