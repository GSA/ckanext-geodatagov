
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
