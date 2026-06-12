<?php
if ( ! defined( 'ABSPATH' ) ) exit;

class RAG_Gemini_Settings {

    public static function init() {
        add_action( 'admin_menu',    [ __CLASS__, 'add_menu' ] );
        add_action( 'admin_init',    [ __CLASS__, 'register_settings' ] );
        add_action( 'admin_enqueue_scripts', [ __CLASS__, 'admin_scripts' ] );
    }

    public static function get( $key, $default = '' ) {
        $settings = get_option( 'rag_gemini_settings', [] );
        return isset( $settings[ $key ] ) ? $settings[ $key ] : $default;
    }

    public static function add_menu() {
        add_options_page(
            'RAG Gemini Chat',
            '🔮 RAG Gemini',
            'manage_options',
            'rag-gemini-chat',
            [ __CLASS__, 'settings_page' ]
        );
    }

    public static function register_settings() {
        register_setting( 'rag_gemini_group', 'rag_gemini_settings', [
            'sanitize_callback' => [ __CLASS__, 'sanitize' ],
        ]);
    }

    public static function sanitize( $input ) {
        return [
            'rag_url'         => esc_url_raw( $input['rag_url'] ?? '' ),
            'widget_title'    => sanitize_text_field( $input['widget_title'] ?? '' ),
            'widget_subtitle' => sanitize_text_field( $input['widget_subtitle'] ?? '' ),
            'accent_color'    => sanitize_hex_color( $input['accent_color'] ?? '#f97316' ),
            'position'        => in_array( $input['position'] ?? '', ['bottom-right','bottom-left'] ) ? $input['position'] : 'bottom-right',
            'show_on_mobile'  => ! empty( $input['show_on_mobile'] ) ? '1' : '0',
            'welcome_message' => sanitize_textarea_field( $input['welcome_message'] ?? '' ),
            'suggestions'     => sanitize_textarea_field( $input['suggestions'] ?? '' ),
        ];
    }

    public static function admin_scripts( $hook ) {
        if ( $hook !== 'settings_page_rag-gemini-chat' ) return;
        wp_enqueue_style( 'wp-color-picker' );
        wp_enqueue_script( 'wp-color-picker' );
    }

    public static function settings_page() {
        if ( ! current_user_can( 'manage_options' ) ) return;
        $s = get_option( 'rag_gemini_settings', [] );
        ?>
        <div class="wrap">
        <h1>🔮 RAG Gemini Chat</h1>
        <p style="color:#666">Widget chat flottant connecté à votre RAG Multimodal Gemini Embedding 2.</p>

        <div style="display:grid;grid-template-columns:1fr 320px;gap:24px;margin-top:20px">
        <div>
        <form method="post" action="options.php">
        <?php settings_fields( 'rag_gemini_group' ); ?>

        <table class="form-table">
            <tr>
                <th>URL de l'API RAG</th>
                <td>
                    <input type="url" name="rag_gemini_settings[rag_url]"
                           value="<?php echo esc_attr( $s['rag_url'] ?? 'https://rag.lhusser.cloud/api/public-query' ); ?>"
                           class="regular-text" placeholder="https://rag.lhusser.cloud/api/public-query"/>
                    <p class="description">Endpoint public de votre RAG (sans authentification).</p>
                </td>
            </tr>
            <tr>
                <th>Titre du widget</th>
                <td>
                    <input type="text" name="rag_gemini_settings[widget_title]"
                           value="<?php echo esc_attr( $s['widget_title'] ?? 'Assistant lhusser.fr' ); ?>"
                           class="regular-text"/>
                </td>
            </tr>
            <tr>
                <th>Sous-titre</th>
                <td>
                    <input type="text" name="rag_gemini_settings[widget_subtitle]"
                           value="<?php echo esc_attr( $s['widget_subtitle'] ?? 'Propulsé par Gemini Embedding 2' ); ?>"
                           class="regular-text"/>
                </td>
            </tr>
            <tr>
                <th>Couleur principale</th>
                <td>
                    <input type="text" name="rag_gemini_settings[accent_color]"
                           value="<?php echo esc_attr( $s['accent_color'] ?? '#f97316' ); ?>"
                           class="rag-color-picker"/>
                    <script>jQuery(document).ready(function($){$('.rag-color-picker').wpColorPicker();});</script>
                </td>
            </tr>
            <tr>
                <th>Position</th>
                <td>
                    <select name="rag_gemini_settings[position]">
                        <option value="bottom-right" <?php selected( $s['position'] ?? 'bottom-right', 'bottom-right' ); ?>>Bas droite</option>
                        <option value="bottom-left"  <?php selected( $s['position'] ?? 'bottom-right', 'bottom-left' ); ?>>Bas gauche</option>
                    </select>
                </td>
            </tr>
            <tr>
                <th>Afficher sur mobile</th>
                <td>
                    <input type="checkbox" name="rag_gemini_settings[show_on_mobile]"
                           value="1" <?php checked( $s['show_on_mobile'] ?? '1', '1' ); ?>/>
                    <label>Afficher le widget sur les appareils mobiles</label>
                </td>
            </tr>
            <tr>
                <th>Message d'accueil</th>
                <td>
                    <textarea name="rag_gemini_settings[welcome_message]" rows="3" class="large-text"><?php
                        echo esc_textarea( $s['welcome_message'] ?? '' );
                    ?></textarea>
                </td>
            </tr>
            <tr>
                <th>Suggestions</th>
                <td>
                    <textarea name="rag_gemini_settings[suggestions]" rows="5" class="large-text"><?php
                        echo esc_textarea( $s['suggestions'] ?? '' );
                    ?></textarea>
                    <p class="description">Une suggestion par ligne. Affiché au démarrage du chat.</p>
                </td>
            </tr>
        </table>

        <?php submit_button( 'Enregistrer les modifications' ); ?>
        </form>
        </div>

        <!-- Aperçu + infos -->
        <div>
            <div style="background:#f9f9f9;border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:16px">
                <h3 style="margin-top:0">📋 Utilisation</h3>
                <p><strong>Shortcode :</strong><br><code>[rag-chat]</code></p>
                <p>À placer dans n'importe quelle page ou article pour afficher le chat inline.</p>
                <p><strong>Widget flottant :</strong><br>
                Activé automatiquement sur toutes les pages.</p>
                <p><strong>Sidebar :</strong><br>
                Apparence → Widgets → <em>RAG Gemini Chat</em></p>
            </div>
            <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px">
                <h3 style="margin-top:0">⚠️ Prérequis</h3>
                <p>L'endpoint RAG doit être accessible publiquement.<br>
                Vérifier que <code>/api/public-query</code> répond sur votre VPS.</p>
                <p><a href="<?php echo esc_url( $s['rag_url'] ?? '' ); ?>" target="_blank" class="button">Tester l'endpoint →</a></p>
            </div>
        </div>
        </div>
        </div>
        <?php
    }
}
