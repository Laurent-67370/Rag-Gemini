<?php
/**
 * Plugin Name:  RAG Gemini Chat
 * Plugin URI:   https://lhusser.fr
 * Description:  Widget chat flottant connecté au RAG Multimodal Gemini Embedding 2
 * Version:      2.2.0
 * Author:       Laurent Husser
 * Author URI:   https://lhusser.fr
 * License:      MIT
 * Text Domain:  rag-gemini-chat
 */

if ( ! defined( 'ABSPATH' ) ) exit;

define( 'RAG_GEMINI_VERSION', '2.2.0' );
define( 'RAG_GEMINI_DIR',     plugin_dir_path( __FILE__ ) );
define( 'RAG_GEMINI_URL',     plugin_dir_url( __FILE__ ) );

// ── Chargement des modules ────────────────────────────────────────
require_once RAG_GEMINI_DIR . 'includes/class-settings.php';
require_once RAG_GEMINI_DIR . 'includes/class-widget.php';
require_once RAG_GEMINI_DIR . 'includes/class-shortcode.php';
require_once RAG_GEMINI_DIR . 'includes/class-frontend.php';

// ── Initialisation ────────────────────────────────────────────────
function rag_gemini_init() {
    RAG_Gemini_Settings::init();
    RAG_Gemini_Widget::init();
    RAG_Gemini_Shortcode::init();
    RAG_Gemini_Frontend::init();
}
add_action( 'plugins_loaded', 'rag_gemini_init' );

// ── Activation ───────────────────────────────────────────────────
register_activation_hook( __FILE__, function() {
    add_option( 'rag_gemini_settings', [
        'rag_url'          => 'https://rag.lhusser.cloud/api/public-query',
        'widget_title'     => 'Assistant lhusser.fr',
        'widget_subtitle'  => 'Propulsé par Gemini Embedding 2',
        'accent_color'     => '#f97316',
        'position'         => 'bottom-right',
        'show_on_mobile'   => '1',
        'welcome_message'  => 'Bonjour ! Je connais tous les articles de ce blog. Pose-moi n\'importe quelle question ! 🔮',
        'suggestions'      => "Quels sont tes derniers articles ?\nComment utiliser Claude Code ?\nQu'est-ce que n8n ?\nComment débuter avec l'IA ?",
    ]);
});

// ── Désactivation ────────────────────────────────────────────────
register_deactivation_hook( __FILE__, function() {
    // Rien à nettoyer
});
