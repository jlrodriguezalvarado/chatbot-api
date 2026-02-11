/**
 * Vinum Chatbot – Admin: color picker and "Aggiorna conoscenza del chatbot" button.
 */
(function () {
    'use strict';

    if (typeof jQuery === 'undefined') return;

    jQuery(function ($) {
        // Color picker for button color
        if ($.fn.wpColorPicker) {
            $('.vinum-color-picker').wpColorPicker();
        }

        // Button image: Media Library picker
        var mediaUploader;
        var $imageInput = $('#vinum_button_image_url');
        var $preview = $('#vinum-button-image-preview');

        function updatePreview() {
            var url = ($imageInput.val() || '').trim();
            $preview.empty();
            if (url && /^https?:\/\//i.test(url)) {
                var img = document.createElement('img');
                img.src = url;
                img.alt = '';
                img.style.cssText = 'max-width:48px;max-height:48px;vertical-align:middle;border:1px solid #ddd;';
                $preview.append(img);
            }
        }
        updatePreview();

        $('#vinum-select-button-image').on('click', function (e) {
            e.preventDefault();
            if (mediaUploader) {
                mediaUploader.open();
                return;
            }
            mediaUploader = wp.media({
                title: 'Select image for chatbot button',
                button: { text: 'Use this image' },
                multiple: false,
                library: { type: 'image' }
            });
            mediaUploader.on('select', function () {
                var attachment = mediaUploader.state().get('selection').first().toJSON();
                $imageInput.val(attachment.url);
                updatePreview();
            });
            mediaUploader.open();
        });

        $('#vinum-remove-button-image').on('click', function () {
            $imageInput.val('');
            updatePreview();
        });

        // Loading GIF: Media Library picker (GIF only)
        var loadingGifUploader;
        var $loadingGifInput = $('#vinum_loading_gif_url');
        var $loadingGifPreview = $('#vinum-loading-gif-preview');

        function updateLoadingGifPreview() {
            var url = ($loadingGifInput.val() || '').trim();
            $loadingGifPreview.empty();
            if (url && /\.gif(\?|$)/i.test(url)) {
                var img = document.createElement('img');
                img.src = url;
                img.alt = '';
                img.style.cssText = 'max-width:48px;max-height:48px;vertical-align:middle;border:1px solid #ddd;';
                $loadingGifPreview.append(img);
            }
        }
        updateLoadingGifPreview();

        $('#vinum-select-loading-gif').on('click', function (e) {
            e.preventDefault();
            if (loadingGifUploader) {
                loadingGifUploader.open();
                return;
            }
            loadingGifUploader = wp.media({
                title: 'Select loading GIF (GIF only)',
                button: { text: 'Use this GIF' },
                multiple: false,
                library: { type: 'image', queryArgs: { post_mime_type: 'image/gif' } }
            });
            loadingGifUploader.on('select', function () {
                var attachment = loadingGifUploader.state().get('selection').first().toJSON();
                if (attachment.mime === 'image/gif') {
                    $loadingGifInput.val(attachment.url);
                    updateLoadingGifPreview();
                } else {
                    alert('Solo se permiten archivos GIF.');
                }
            });
            loadingGifUploader.open();
        });

        $('#vinum-remove-loading-gif').on('click', function () {
            $loadingGifInput.val('');
            updateLoadingGifPreview();
        });

        // Refresh knowledge button
        $('#vinum-refresh-knowledge').on('click', function () {
            var $btn = $(this);
            var $status = $('#vinum-refresh-status');
            var refreshUrl = typeof vinumChatbotAdmin !== 'undefined' && vinumChatbotAdmin.refreshUrl
                ? vinumChatbotAdmin.refreshUrl
                : '';
            var apiKey = typeof vinumChatbotAdmin !== 'undefined' && vinumChatbotAdmin.apiKey
                ? vinumChatbotAdmin.apiKey
                : '';
            var i18n = typeof vinumChatbotAdmin !== 'undefined' && vinumChatbotAdmin.i18n
                ? vinumChatbotAdmin.i18n
                : { refreshing: 'Refrescando...', done: 'Hecho', error: 'Error al refrescar' };

            if (!refreshUrl) {
                $status.css('color', '#b32d2e').text(i18n.error + ' (URL non configurata)');
                return;
            }

            $btn.prop('disabled', true);
            $status.css('color', '').text(i18n.refreshing);

            var headers = { 'Content-Type': 'application/json' };
            if (apiKey) {
                headers['Authorization'] = 'Bearer ' + apiKey;
            }

            fetch(refreshUrl, {
                method: 'POST',
                headers: headers,
                credentials: 'omit'
            })
                .then(function (res) {
                    return res.json().catch(function () { return {}; }).then(function (data) {
                        if (res.ok) {
                            var msg = (res.status === 202 && data.message) ? data.message : i18n.done;
                            $status.css('color', '#00a32a').text(msg);
                        } else {
                            throw new Error(data.error || 'HTTP ' + res.status);
                        }
                    });
                })
                .catch(function () {
                    $status.css('color', '#b32d2e').text(i18n.error);
                })
                .finally(function () {
                    $btn.prop('disabled', false);
                });
        });
    });
})();
