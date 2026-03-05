import type { LanguageCode } from "../../types";

export const USER_ASSISTANT_MESSAGES: Record<LanguageCode, Record<string, unknown>> = {
  "en": {
    "userPortal": {
      "title": "User Portal",
      "description": "Describe your issue in chat and send it directly to the help desk.",
      "heroTitle": "Fast lane support",
      "heroSubtitle": "Share the problem, get triaged, and route to the right specialist in one flow.",
      "emptyState": "Hi! Describe your issue below, or try one of the quick prompts.",
      "placeholder": "Describe your issue...",
      "submit": "Send",
      "sending": "Sending...",
      "reset": "New conversation",
      "sampleWifi": "My laptop won't connect to WiFi",
      "samplePasswordReset": "I need a password reset",
      "sampleSoftware": "Software installation request",
      "defaultAgent": "Help Desk Triage Agent"
    }
  },
  "es": {
    "userPortal": {
      "title": "Portal de Usuario",
      "description": "Describe tu problema en el chat y envíalo directamente a la mesa de ayuda.",
      "heroTitle": "Soporte en vía rápida",
      "heroSubtitle": "Comparte el problema, recibe triaje y llega al especialista correcto en un solo flujo.",
      "emptyState": "¡Hola! Describe tu problema abajo o prueba una opción rápida.",
      "placeholder": "Describe tu problema...",
      "submit": "Enviar",
      "sending": "Enviando...",
      "reset": "Nueva conversación",
      "sampleWifi": "Mi laptop no se conecta al WiFi",
      "samplePasswordReset": "Necesito restablecer mi contraseña",
      "sampleSoftware": "Solicitud de instalación de software",
      "defaultAgent": "Agente de Triaje de Mesa de Ayuda"
    }
  }
};
