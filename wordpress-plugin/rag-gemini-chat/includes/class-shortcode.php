<?php
if ( ! defined( 'ABSPATH' ) ) exit;

class RAG_Gemini_Shortcode {

    public static function init() {
        add_shortcode( 'rag-chat', [ __CLASS__, 'render' ] );
        add_shortcode( 'rag_chat', [ __CLASS__, 'render' ] );
    }

    public static function render( $atts ) {
        $atts = shortcode_atts([
            'height'      => '500px',
            'placeholder' => 'Pose ta question…',
            'title'       => '',
        ], $atts, 'rag-chat' );

        $id = 'rag-inline-' . uniqid();
        ob_start();
        ?>
        <div id="<?php echo esc_attr($id); ?>" class="rag-gemini-inline"
             data-height="<?php echo esc_attr($atts['height']); ?>"
             data-placeholder="<?php echo esc_attr($atts['placeholder']); ?>"
             data-title="<?php echo esc_attr($atts['title']); ?>"
             style="height:<?php echo esc_attr($atts['height']); ?>;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#0f172a;">
        </div>
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof ragGeminiInline === 'function') {
                ragGeminiInline('<?php echo esc_js($id); ?>');
            }
        });
        </script>
        <?php
        return ob_get_clean();
    }
}
