this.ckan.module('geodatagov-site-wide-search', function($, _) {
  return {
    options: {
      base_url: 'http://54.204.35.58/search/node/'
    },
    initialize: function() {
      var el = this.el;
      var options = this.options;
      $("#field-sitewide-search").change(function(){
        el.attr('action', options.base_url + this.value);
      });
      this.el.submit(function(){
        window.location.href = $(this).attr('action');
        return false;
      });
    }
  }
});

this.ckan.module('geodatagov-search-helper-message', function($, _) {
  return {
    options: {},
    initialize: function() {
      var el = this.el;
      var popup = $('#search-helper-message');
      el
        .on('mouseover', function() {
          popup.show();
        })
        .on('mouseout', function() {
          popup.hide();
        });
      if ($('html').hasClass('ie7')) {
        function position() {
          var offset = el.offset();
          popup
            .css('left', offset.left - popup.outerWidth() + el.outerWidth())
            .css('top', offset.top + el.outerHeight() + 5);
        }
        popup.appendTo('body');
        position();
        $(window).on('resize', position);
      }
    }
  };
});
