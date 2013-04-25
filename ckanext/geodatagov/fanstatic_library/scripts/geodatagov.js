
this.ckan.module('geodatagov-top-nav', function($, _) {
  return {
    options: {},
    initialize: function() {
      var html = $('html');
      var page = window.location.pathname;
      $('[data-check]', this.el).each(function() {
        var $this = $(this);
        if ($this.data('check') == page) {
          $this.addClass('active');
        }
      });
      if (html.hasClass('ie7') || html.hasClass('ie8')) {
        $('input, textarea').placeholder();
      }
    }
  };
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
