<?php
if ( ! defined( 'ABSPATH' ) ) exit;

class RAG_Gemini_Widget extends WP_Widget {

    public static function init() {
        add_action( 'widgets_init', function() {
            register_widget( 'RAG_Gemini_Widget' );
        });
    }

    public function __construct() {
        parent::__construct(
            'rag_gemini_chat',
            '🔮 RAG Gemini Chat',
            [ 'description' => 'Chat connecté au RAG Multimodal Gemini Embedding 2' ]
        );
    }

    public function widget( $args, $instance ) {
        $title  = ! empty( $instance['title'] ) ? $instance['title'] : 'Assistant IA';
        $height = ! empty( $instance['height'] ) ? $instance['height'] : '400px';
        echo $args['before_widget'];
        echo $args['before_title'] . esc_html($title) . $args['after_title'];
        echo do_shortcode( '[rag-chat height="' . esc_attr($height) . '" title="' . esc_attr($title) . '"]' );
        echo $args['after_widget'];
    }

    public function form( $instance ) {
        $title  = ! empty( $instance['title'] ) ? $instance['title'] : 'Assistant IA';
        $height = ! empty( $instance['height'] ) ? $instance['height'] : '400px';
        ?>
        <p>
            <label for="<?php echo $this->get_field_id('title'); ?>">Titre :</label>
            <input class="widefat" id="<?php echo $this->get_field_id('title'); ?>"
                   name="<?php echo $this->get_field_name('title'); ?>"
                   type="text" value="<?php echo esc_attr($title); ?>"/>
        </p>
        <p>
            <label for="<?php echo $this->get_field_id('height'); ?>">Hauteur :</label>
            <input class="widefat" id="<?php echo $this->get_field_id('height'); ?>"
                   name="<?php echo $this->get_field_name('height'); ?>"
                   type="text" value="<?php echo esc_attr($height); ?>"/>
            <small>Ex: 400px, 500px</small>
        </p>
        <?php
    }

    public function update( $new_instance, $old_instance ) {
        return [
            'title'  => sanitize_text_field( $new_instance['title'] ?? '' ),
            'height' => sanitize_text_field( $new_instance['height'] ?? '400px' ),
        ];
    }
}
