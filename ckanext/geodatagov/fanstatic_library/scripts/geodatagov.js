
this.ckan.module('geodatagov-top-nav', function($, _) {
  return {
    options: {},
    initialize: function() {
      var page = window.location.pathname;
      $('[data-check]', this.el).each(function() {
        var $this = $(this);
        if ($this.data('check') == page) {
          $this.addClass('active');
        }
      });
    }
  };
});

this.ckan.module('geodatagov-search-helper-message', function($, _) {
  return {
    options: {},
    initialize: function() {
      var popup = $('#search-helper-message');
      this.el
        .on('mouseover', function() {
          popup.show();
        })
        .on('mouseout', function() {
          popup.hide();
        });
    }
  };
});
