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

function GetURLParameter(sParam) {
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++)  {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam) 
            return sParameterName[1];        		
    }
	
    return 0;
}


$(document).ready(function () {

    var sort = GetURLParameter('sort');	
    var q = GetURLParameter('q');	
	
	if(sort == 0 && q == 0)
	   $("#sort_option").html("Datasets ordered by Popular");
	else if(sort == 'none') {
	   $("#sort_option").html("Datasets ordered by Relevance");
	   $("#field-order-by").val('score desc, name asc');
	}
	else {
	$("#field-order-by option[value='none']").remove();
	   var sortVal = decodeURIComponent(sort).replace(/\+/g, ' ');	   
	   var sortTxt = $("#field-order-by option[value='" + sortVal + "']").text();
	   $("#sort_option").html("Datasets ordered by " + sortTxt);
	}
	
    // let's check if we just came from data.gov community
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
                && (referrer.indexOf('catalog') < 0) && (referrer.indexOf('ckan') < 0));
        }

        if (fromDataGov) {
            if (document.URL.indexOf('/dataset') > 0
                || document.URL.indexOf('groups=') >0
                || document.URL.indexOf('/group/') >0
                || document.URL.indexOf('/organization/') >0)
            {
                $.cookie('back2community', document.referrer,{ path: "/", expires: 2 });
                if ((matches = document.location.hash.match(/#topic=([\S_-]+)/)) && (typeof matches[1] !== 'undefined')) {
                    $.cookie('community_hash', matches[1],{ path: "/", expires: 2 });
                }

            } else {
//            if it is just search, we should remove this cookie
                $.removeCookie('back2community');
                $.removeCookie('community_hash');

            }
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

// fix for dynamic menu to check current domain and assign menu

jQuery(window).load(function(){
    if (window.location.hostname==='catalog.data.gov'){
        var linkRewriter = function(a, b) {
            $('a[href*="' + a + '"]').each(function() {
                $(this).attr('href', $(this).attr('href').replace(a, b));
            });
        }

        linkRewriter("next.data.gov", "data.gov");
    }else if (window.location.hostname==='staging.catalog.data.gov'){
        var linkRewriter = function(a, b) {
            $('a[href*="' + a + '"]').each(function() {
                $(this).attr('href', $(this).attr('href').replace(a, b));
            });
        }

        linkRewriter("next.data.gov", "staging.data.gov");

    }

 //   window.location.hash = "";
   
});

if ($.browser.msie && $.browser.version == 10) {
    $("html").addClass("ie10");
}
window.onload=function(){
    if (!jQuery("#menu-community a[href*='catalog']").hasClass('active')) {
         jQuery("#menu-community a[href*='catalog']").addClass('active');
    }
    jQuery("#content .toolbar .breadcrumb .active a").prop("href", document.URL);
	
}

$(document).ready(function () {
	    if (document.domain.indexOf('data.gov') > -1) {
	document.domain="data.gov";
	}
	if (document.domain.indexOf('reisys.com') > -1) {
	document.domain="reisys.com";
	}
    dataproxy = 'http://jsonpdataproxy.appspot.com';
    function test_to_preview(elem) {
        ext_href = elem.next().attr('href')
        var apiurl = dataproxy + '?url=' + ext_href;
        $.ajax({
            url: apiurl,
            dataType: 'jsonp',
            success: function(data){
                if (data.error) return;
                elem.css('display', 'inline-block');
            }
        });
    }

    $('.btn-preview').each(function() {
        test_to_preview($(this))
    });


});
