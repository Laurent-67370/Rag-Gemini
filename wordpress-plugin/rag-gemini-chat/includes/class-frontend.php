<?php
if ( ! defined( 'ABSPATH' ) ) exit;

class RAG_Gemini_Frontend {

    public static function init() {
        add_action( 'wp_enqueue_scripts', [ __CLASS__, 'enqueue' ] );
        add_action( 'wp_footer',          [ __CLASS__, 'render_widget' ] );
    }

    public static function enqueue() {
        wp_enqueue_style(
            'rag-gemini-chat',
            RAG_GEMINI_URL . 'assets/rag-widget-' . RAG_GEMINI_VERSION . '.css',
            [],
            RAG_GEMINI_VERSION
        );
        wp_enqueue_script(
            'rag-gemini-chat',
            RAG_GEMINI_URL . 'assets/rag-widget-' . RAG_GEMINI_VERSION . '.js',
            [],
            RAG_GEMINI_VERSION,
            true // footer
        );
        // Passer la config PHP → JS
        wp_localize_script( 'rag-gemini-chat', 'ragGeminiConfig', [
            'rag_url'         => RAG_Gemini_Settings::get( 'rag_url', 'https://rag.lhusser.cloud/api/public-query' ),
            'widget_title'    => RAG_Gemini_Settings::get( 'widget_title', 'Assistant lhusser.fr' ),
            'widget_subtitle' => RAG_Gemini_Settings::get( 'widget_subtitle', 'Propulsé par Gemini Embedding 2' ),
            'accent_color'    => RAG_Gemini_Settings::get( 'accent_color', '#f97316' ),
            'position'        => RAG_Gemini_Settings::get( 'position', 'bottom-right' ),
            'show_on_mobile'  => RAG_Gemini_Settings::get( 'show_on_mobile', '1' ),
            'welcome_message' => RAG_Gemini_Settings::get( 'welcome_message', '' ),
            'suggestions'     => array_filter( array_map( 'trim',
                explode( "\n", RAG_Gemini_Settings::get( 'suggestions', '' ) )
            )),
        ]);
    }

    public static function render_widget() {
        // Le widget flottant est injecté par JS — rien à rendre ici
        // sauf le conteneur vide pour le shortcode inline
    }
}
