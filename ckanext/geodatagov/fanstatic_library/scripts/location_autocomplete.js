/* An auto-complete module for the locations API endpoint
 *
 *
 */
this.ckan.module('location-autocomplete', function (jQuery, _) {
  return {
    /* Options for the module */
    options: {
      tags: false,
      key: false,
      label: false,
      items: 10,
      source: null,
      interval: 500,
      dropdownClass: '',
      containerClass: '',
      i18n: {
        noMatches: _('No matches found'),
        emptySearch: _('Start typing…'),
        inputTooShort: function (data) {
          return _('Input is too short, must be at least one character')
          .ifPlural(data.min, 'Input is too short, must be at least %(min)d characters');
        }
      }
    },

    /* Sets up the module, binding methods, creating elements etc. Called
     * internally by ckan.module.initialize();
     *
     * Returns nothing.
     */
    initialize: function () {
      jQuery.proxyAll(this, /_on/, /format/);

      this.setupAutoComplete();

      this.el.ready(this._onReady);
    },

    /* Sets up the auto complete plugin.
     *
     * Returns nothing.
     */
    setupAutoComplete: function () {
      var module = this;
      module.form = $("#dataset-search");
      var previous_location = this._getParameterByName('ext_location');
      var settings = {
        width: 'resolve',
        formatResult: this.formatResult,
        formatSelection: this.formatSelection,
        formatNoMatches: this.formatNoMatches,
        formatInputTooShort: this.formatInputTooShort,
        dropdownCssClass: this.options.dropdownClass,
        containerCssClass: this.options.containerClass,
        minimumInputLength: 3,
        ajax: {
          url: this.options.source,
          dataType: 'json',
          quietMillis: this.options.interval,
          data: function(term, page) {
            return { q: term}
          },
          results: function(data, page) {
            module._locationsRegistry = {};
            jQuery.map(data.result, function(item) {
              module._locationsRegistry[item.id] = {};
              module._locationsRegistry[item.id]['text'] = item.text;
              module._locationsRegistry[item.id]['geom'] = item.geom;
            });

          return {results: data.result}
         }
        },

        initSelection: (previous_location) ? function(element, callback){
          callback({id: '', text: previous_location})} : false

      };

      var select2 = this.el.select2(settings).data('select2');

      // Save the location to the ext_location field when selecting and publish
      // the change so the map can update the bbox shown
      this.el.on('change', function(e){
        dropdownChange(e.val);
      });

      function dropdownChange(value) {
        if (value && module._locationsRegistry[value] && module._locationsRegistry[value].geom){
          var geom = module._locationsRegistry[value].geom;

          var minx = Math.min(geom['coordinates'][0][2][0], geom['coordinates'][0][0][0]);
          var miny = Math.min(geom['coordinates'][0][2][1], geom['coordinates'][0][0][1]);
          var maxx = Math.max(geom['coordinates'][0][2][0], geom['coordinates'][0][0][0]);
          var maxy = Math.max(geom['coordinates'][0][2][1], geom['coordinates'][0][0][1]);

          var bbox = [minx, miny, maxx, maxy].join()

          $('#ext_location').val(module._locationsRegistry[value].text);
          $('#ext_prev_extent').val('');
          $('#ext_bbox').val(bbox);

          module.form.submit();
        }
      }

      if (this.options.tags && select2 && select2.search) {
        // find the "fake" input created by select2 and add the keypress event.
        // This is not part of the plugins API and so may break at any time.
        select2.search.on('keydown', this._onKeydown);
      }

      // Please forgive me for this horrible hack for IE<9
      // Basically module.el.on('change') doesn't trigger and module.el.val()
      // doesn't return a value... so this is what I came up with... I makes me
      // feel dirty knowing that this piece of code exists in the world.
      if ($('html').hasClass('ie9') || $('html').hasClass('ie8') || $('html').hasClass('ie7')) {
        var ie_current_value = module.el.val() || 'Enter location...';
        setInterval(function() {
          var element = $('input', module.el.parent());
          if (typeof element[0] != 'undefined' && element[0].value) {
            var check = element[0].value;
            if (check != ie_current_value) {
              ie_current_value = check;
              dropdownChange(check);
            }
          }
        }, 100);
      }
    },

    /* Formatter for the select2 plugin that returns a string for use in the
     * results list with the current term emboldened.
     *
     * state     - The current object that is being rendered.
     * container - The element the content will be added to (added in 3.0)
     * query     - The query object (added in select2 3.0).
     *
     *
     * Returns a text string.
     */
    formatResult: function (result, container, query) {
      var term = this._lastTerm || null; // same as query.term

      if (container) {
        // Append the select id to the element for styling.
        container.attr('data-value', result.id);
      }

      return result.text.split(term).join(term && term.bold());
    },

    /* Formatter for the select2 plugin that returns a string used when
     * the filter has no matches.
     *
     * Returns a text string.
     */
    formatNoMatches: function (term) {
      return !term ? this.i18n('emptySearch') : this.i18n('noMatches');
    },

    /* Formatter used by the select2 plugin that returns a string when the
     * input is too short.
     *
     * Returns a string.
     */
    formatInputTooShort: function (term, min) {
      return this.i18n('inputTooShort', {min: min});
    },


    _getParameterByName: function (name) {
      var match = RegExp('[?&]' + name + '=([^&]*)')
                        .exec(window.location.search);
      return match ?
          decodeURIComponent(match[1].replace(/\+/g, ' '))
          : null;
    },

    /* Callback triggered when the element is ready, so we eg can modify the DOM.
     *
     * Returns nothing.
     */
    _onReady: function () {
      var module = this;
      var previous_location = module._getParameterByName('ext_location');

      // Add necessary fields to the search form if not already created
      $('<input type="hidden" />').attr({'id': 'ext_location', 'name': 'ext_location'}).appendTo("#dataset-search");
      $(['ext_bbox', 'ext_prev_extent']).each(function(index, item){
        if ($("#" + item).length === 0) {
          $('<input type="hidden" />').attr({'id': item, 'name': item}).appendTo(module.form);
        }
      });

      if (previous_location) {
        $('#ext_location').val(previous_location);
      }

    }

  };
});
