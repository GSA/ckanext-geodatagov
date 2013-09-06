this.ckan.module('geodatagov-site-wide-search', function($, _) {
  return {
    options: {
      base_url: 'http://www.data.gov/search/node/'
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
jQuery(function($){
    $(document).ready(function () {
        var referralCookie = document.referrer.indexOf(window.location.origin);
        if (referralCookie=='-1') {
            referralCookie = document.referrer;
            $.cookie('datagov', referralCookie,{ path: "/", expires: 2 });
        }
        var cookie = $.cookie("datagov");
        if (cookie!=''){
            $('#exitURL').css('display','block');
        }
    });
});

jQuery('#exitURL').click(function(){
    var referralCookie = jQuery.cookie('datagov');
    //jQuery.cookie('datagov', '');
    window.location.replace(referralCookie);
});