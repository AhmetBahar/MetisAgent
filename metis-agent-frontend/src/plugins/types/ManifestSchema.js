// src/plugins/types/ManifestSchema.js
/**
 * Plugin Manifest Schema
 * Standart plugin manifest yapısı
 */

export const ManifestSchema = {
    type: "object",
    properties: {
      id: {
        type: "string",
        description: "Plugin benzersiz ID"
      },
      name: {
        type: "string",
        description: "Plugin görünen adı"
      },
      description: {
        type: "string",
        description: "Plugin açıklaması"
      },
      version: {
        type: "string",
        description: "Plugin sürümü (semver)"
      },
      author: {
        type: "string",
        description: "Plugin yazarı"
      },
      license: {
        type: "string",
        description: "Plugin lisansı"
      },
      type: {
        type: "string",
        enum: ["persona", "tool", "workflow"],
        description: "Plugin tipi"
      },
      icon: {
        type: "string",
        description: "Plugin ikonu (Lucide icon adı)"
      },
      capabilities: {
        type: "array",
        items: {
          type: "string"
        },
        description: "Plugin yetenekleri"
      },
      conversation_flow: {
        type: "string",
        enum: ["chat_guided", "form_based", "mixed"],
        default: "chat_guided",
        description: "Etkileşim akış tipi"
      },
      workflow_steps: {
        type: "array",
        items: {
          type: "object",
          properties: {
            id: { type: "string" },
            label: { type: "string" },
            description: { type: "string" }
          },
          required: ["id", "label"]
        },
        description: "İş akışı adımları"
      },
      required_context: {
        type: "array",
        items: {
          type: "object",
          properties: {
            id: { type: "string" },
            type: { type: "string" },
            description: { type: "string" }
          },
          required: ["id", "type"]
        },
        description: "İhtiyaç duyulan bilgiler"
      },
      apis: {
        type: "object",
        properties: {
          execute: { type: "string" }
        },
        description: "API endpoint'leri"
      },
      ui: {
        type: "object",
        properties: {
          primaryColor: { type: "string" },
          layout: { type: "string" },
          showContextInPanel: { type: "boolean" }
        },
        description: "UI yapılandırması"
      }
    },
    required: ["id", "name", "type"]
  };
  
  export default ManifestSchema;