// 5. src/components/persona/plugins/social-media/index.js
// Sosyal Medya Persona Plugin giriş noktası

import React from 'react';
import SocialMediaView from './SocialMediaView';

/**
 * Social Media Persona Plugin
 */
const SocialMediaPersona = (props) => <SocialMediaView {...props} />;

// Plugin meta verileri
const manifest = {
  id: "social-media",
  name: "Sosyal Medya Asistanı",
  description: "Instagram, Twitter ve diğer sosyal medya platformları için içerik üretimi",
  icon: "Users",
  version: "1.0.0",
  author: "Metis Team",
  capabilities: ["content_creation", "hashtag_management", "social_media_plan"],
  requires: ["core:chat", "core:editor"],
  ui: {
    primaryColor: "#E1306C",
    layout: "workflow"
  }
};

// Plugin meta verileri ve bileşen birleştirmesi
export default {
  ...manifest,
  component: SocialMediaPersona
};