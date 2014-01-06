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

$(document).ready(function () {
//    let's check if we just came from data.gov community
    if ('' !== document.referrer) {
        var parts = document.referrer.split( '/' );

        for(var i=0; i < parts.length; i++) {
            if (parts[i].length > 6) {
                var referrer = parts[i];
                break;
            }
        }

        var fromDataGov = false;

        if (typeof referrer !== 'undefined') {
            fromDataGov = ((referrer.indexOf('datagov') > -1 || (referrer.indexOf('data.gov') > -1))
                && (referrer.indexOf('catalog') < 0 || referrer.indexOf('ckan') < 0));
        }

        if (fromDataGov &&
            (document.URL.indexOf('/dataset/') > 0
                || document.URL.indexOf('groups=') >0
                || document.URL.indexOf('/group/') >0
                || document.URL.indexOf('/organization/') >0))
        {
            $.cookie('back2community', document.referrer,{ path: "/", expires: 2 });
        } else {
//            if it is just search, we should remove this cookie
            $.removeCookie('back2community');
        }
    }

//    now let's show the button if needed
    if (($('#exitURL').length > 0)) {

        var cookie = $.cookie('back2community');
        
        if ((typeof cookie !== 'undefined') && ('' !== cookie)) {
            $('#exitURL').click(function(){
                $.removeCookie('back2community');
                window.location.replace(cookie);
            });
            $('#exitURL').attr('href', cookie);
            $('#exitURL').show();
        } else {
            $('#exitURL').hide();
        }
    }
});
//adding dynamic menu
(function($) {

    var url = '//next.data.gov/wp-content/plugins/datagov-custom/wp_download_links.php?callback=?';
    $.ajax({
        type: 'GET',
        url: url,
        async: false,
        jsonpCallback: 'jsonCallback',
        contentType: "application/json",
        dataType: 'jsonp',
        success: function(json) {
            var menus = [];
            var topmenus=[];
            var topsecondarys=[];
            $.each(json.Footer, function(i,menu){
                menus.push('<li><a href="' +menu.link + '">' +menu.name + '</a></li>');
            });
            $.each(json.Primary, function(i,topmenu){
                if(!topmenu.parent_id) {
                    if(topmenu.name=='Topics'){
                        topmenus.push('<li class="dropdown menu-topics"><a data-toggle="dropdown" class="dropdown-toggle">Topics<b class="caret"></b></a><ul class="dropdown-menu"></ul></li>');
                    }else{
                        topmenus.push('<li><a href="' +topmenu.link + '">' +topmenu.name + '</a></li>');
                    }
                }
            });
            $.each(json.Primary, function(i,topsecondary){
                if(topsecondary.parent_id ) {
                    topsecondarys.push('<li><a href="' +topsecondary.link + '">' +topsecondary.name + '</a></li>');
                }
            });
            $('#menu-primary-navigation').append( topmenus.join('') );
            $('#menu-primary-navigation .dropdown-menu').append( topsecondarys.join('') );
            $('#menu-primary-navigation-1').append( topmenus.join('') );
            $('#menu-footer').prepend(menus.join('') );
            $('#menu-primary-navigation-1 .dropdown-menu').append( topsecondarys.join('') );
        },
        error: function(e) {
            console.log(e.message);
        }
    });
})(jQuery);
// fix for dynamic menu to check current domain and assign menu

jQuery(window).load(function(){
    if (window.location.hostname==='catalog.data.gov'){
        var linkRewriter = function(a, b) {
            $('a[href*="' + a + '"]').each(function() {
                $(this).attr('href', $(this).attr('href').replace(a, b));
            });
        }

        linkRewriter("next.data.gov", "data.gov");
    }
});