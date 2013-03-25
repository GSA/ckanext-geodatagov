/* An auto-complete module for select and input elements that can pull in
 * a list of terms from an API endpoint (provided using data-module-source).
 *
 * source   - A url pointing to an API autocomplete endpoint.
 * interval - The interval between requests in milliseconds (default: 1000).
 * items    - The max number of items to display (default: 10)
 * tags     - Boolean attribute if true will create a tag input.
 * key      - A string of the key you want to be the form value to end up on
 *            from the ajax returned results
 * label    - A string of the label you want to appear within the dropdown for
 *            returned results
 *
 * Examples
 *
 *   // <input name="tags" data-module="autocomplete" data-module-source="http://" />
 *
 */
// Dataset map module
this.ckan.module('spatial-query', function (jQuery, _) {

  return {
    options: {
      i18n: {
      },
      style: {
        color: '#B52',
        weight: 2,
        opacity: 1,
        fillColor: '#FCF6CF',
        fillOpacity: 0.4
      },
      default_extent: [[15.62, -139.21], [64.92, -61.87]] //TODO: customize
      //[[90, 180], [-90, -180]]
    },

    initialize: function () {
      var module = this;

      jQuery.proxyAll(this, /_on/);

      this.el.ready(this._onReady);

    },

    _getParameterByName: function (name) {
      var match = RegExp('[?&]' + name + '=([^&]*)')
                        .exec(window.location.search);
      return match ?
          decodeURIComponent(match[1].replace(/\+/g, ' '))
          : null;
    },

    _drawExtentFromCoords: function(xmin, ymin, xmax, ymax) {
        if (jQuery.isArray(xmin)) {
            var coords = xmin;
            xmin = coords[0]; ymin = coords[1]; xmax = coords[2]; ymax = coords[3];
        }
        return new L.Rectangle([[ymin, xmin], [ymax, xmax]],
                               this.options.style);
    },

    _drawExtentFromGeoJSON: function(geom) {
        return new L.GeoJSON(geom, {style: this.options.style});
    },

    _onReady: function() {

      var module = this;
      var map, backgroundLayer, extentLayer, drawControl, previous_box,
          previous_extent;

      // Add necessary fields to the search form
      $(['ext_bbox', 'ext_prev_extent']).each(function(index, item){
        $('<input type="hidden" />').attr({'id': item, 'name': item}).appendTo("#dataset-search");
      });

      map = new L.Map('dataset-map-container', {attributionControl: false});

      // MapQuest OpenStreetMap base map
      backgroundLayer = new L.TileLayer(
        'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
         {maxZoom: 18, subdomains: '1234'}
      );
      map.addLayer(backgroundLayer);

      // Initialize the draw control
      drawControl = new L.Control.Draw({
          polyline: false, polygon: false,
          circle: false, marker: false,
          rectangle: {
            shapeOptions: this.options.style
          }
      });
      map.addControl(drawControl);

      // When user finishes drawing the box, record it and add it to the map
      map.on('draw:rectangle-created', function (e) {
          if (extentLayer){
            map.removeLayer(extentLayer);
          }
          extentLayer = e.rect;
          $('#ext_bbox').val(extentLayer.getBounds().toBBoxString());
          map.addLayer(extentLayer);
      });

      // Record the current map view so we can replicate it after submitting
      map.on('moveend', function(e) {
        $('#ext_prev_extent').val(map.getBounds().toBBoxString());
      });

      // Listen to changes in extent (ie location search box)
      this.sandbox.subscribe('change:location', function (location_) {
        if (extentLayer){
          map.removeLayer(extentLayer);
        }
        extentLayer = module._drawExtentFromGeoJSON(location_.geom);
        map.fitBounds(extentLayer.getBounds());
        map.addLayer(extentLayer);
        $('#ext_bbox').val(extentLayer.getBounds().toBBoxString());
      });

      // Is there an existing box from a previous search?
      previous_bbox = this._getParameterByName('ext_bbox');
      if (previous_bbox) {
        $('#ext_bbox').val(previous_bbox);
        extentLayer = this._drawExtentFromCoords(previous_bbox.split(','))
        map.addLayer(extentLayer);
      }

      // Is there an existing extent from a previous search?
      previous_extent = this._getParameterByName('ext_prev_extent');
      if (previous_extent) {
        coords = previous_extent.split(',');
        map.fitBounds([[coords[1], coords[0]], [coords[3], coords[2]]]);
      } else {
        map.fitBounds(this.options.default_extent);
      }
    }
  }
});
