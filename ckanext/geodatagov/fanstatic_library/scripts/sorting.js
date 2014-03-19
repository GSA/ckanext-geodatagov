jQuery( document ).ready(function() {

    /**
     * for Alphabatical sort set param 'sortType' to alpha
     * for Count sort set param 'sortType' to count
     * for sort order set param 'sort' to asc or desc
     **/
    var defaults = {
        'metadata_type' : {'sortType': 'count', 'sort' : 'desc'},
        'tags' : {'sortType': 'count', 'sort' : 'desc'},
        'res_format' : {'sortType': 'alpha', 'sort' : 'asc'},
        'groups' : {'sortType': 'count', 'sort' : 'desc'},
        'organization_type' : {'sortType': 'count', 'sort' : 'desc'},
        'organization' : {'sortType': 'count', 'sort' : 'desc'},
        'vocab_category_all' : {'sortType': 'count', 'sort' : 'desc'},
        'dataset_type' : {'sortType': 'count', 'sort' : 'desc'},
        'harvest_source_title' : {'sortType': 'count', 'sort' : 'desc'},
        'frequency' : {'sortType': 'count', 'sort' : 'desc'},
        'source_type' : {'sortType': 'count', 'sort' : 'desc'},
		'publisher' : {'sortType': 'count', 'sort' : 'desc'}
        //'extras_progress' : {'sortType': 'count', 'sort' : 'desc'}
    };

    $.extend({
        getUrlVars: function(){
            var vars = [], hash;
            var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
            for(var i = 0; i < hashes.length; i++) {
                hash = hashes[i].split('=');
                vars.push(hash[0]);
                vars[hash[0]] = hash[1];
            }
            return vars;
        },

        getUrlVar: function(name){
            return $.getUrlVars()[name];
        }
    });

    var allVars = $.getUrlVars();
    var paramArr=[];
    var defaultArr = defaults;

    if(allVars[0] != window.location.href) {

        for(var i = 0; i < allVars.length; i++) {

            var sort = $.getUrlVar(allVars[i]).split('#')[0];

            if(sort == 'asc' || sort == 'desc') {

                var id, sortType;
                var parts = allVars[i].split('_');

                if(parts[parts.length-1] == 'sortAlpha')
                    sortType = 'alphaSort';
                else
                    sortType = 'cntSort';

                if(parts.length > 3) {
                    parts.splice(0,1);
                    parts.splice(parts.length-1, 1);

                    id = parts.join('_');
                }
                else
                    id = parts[1];

                paramArr.push(id);
                var url = $('#' + id).parent().parent().find('p.module-footer a.read-more').attr('href');

                if(typeof(url) == 'undefined')
                    return;

                if(url.indexOf('_' + id + '_limit=0') == -1)
                    url = url + '&_' + id + '_limit=0';

                //original list
                var mylist1 = $('ul.unstyled.nav.nav-simple.nav-facet#' + id);
                var cnt = mylist1.children('li').get().length;
                mylist1.html("");

                imageChange(sortType, id, sort);
                sortFacet(url, id, mylist1, sort, cnt, sortType);

            }
        }//end of for

        var diff = {};
        $.each(defaults, function(i,e) {
            if ($.inArray(i, paramArr) == -1) {
                diff['' + i + ''] = e;
            }
        });

        defaultArr = diff;
    }

    $.each(defaultArr, function(key, value) {

        var sortType;
        if(defaultArr[key]['sortType'] == 'alpha')
            sortType = 'alphaSort';
        else
            sortType = 'cntSort';

        var sort = defaultArr[key]['sort'];

        imageChange(sortType, key, sort);

        var url = $('#' + key).parent().parent().find('p.module-footer a.read-more').attr('href');

        if(typeof(url) == 'undefined')
            return;

        if(url.indexOf('_' + key + '_limit=0') == -1) {
            if(url.indexOf('?') == -1)
                url = url + '?_' + key + '_limit=0';
            else
                url = url + '&_' + key + '_limit=0';
        }

        url = url + '#' + key;

        //original list
        var mylist1 = $('ul.unstyled.nav.nav-simple.nav-facet#' + key);
        var cnt = mylist1.children('li').get().length;
        mylist1.html("");

        sortFacet(url, key, mylist1, sort, cnt, sortType);
    });


    $("img#sortFacetAlpha").click(function() {

        //get id of current facet
        var id = $(this).parent().parent().find('ul.unstyled.nav.nav-simple.nav-facet').attr('id');
        var url = $(this).parent().parent().find('p.module-footer a.read-more').attr('href');

        if(typeof(url) == 'undefined')
            return;

        var browserURL = window.location.href;

        if(browserURL.indexOf('#') != -1)
            browserURL = browserURL.substring(0, browserURL.indexOf('#'));


        //original list
        var mylist1 = $('ul.unstyled.nav.nav-simple.nav-facet#' + id);
        var cnt = mylist1.children('li').get().length;
        mylist1.html("");

        if(mylist1.hasClass('alph_asc')) {

            var sort = 'desc';

            if(url.indexOf('_' + id + '_sortAlpha') != -1)
                url = url.replace('_' + id + '_sortAlpha=asc', '_' + id + '_sortAlpha=desc');
            else {
                if(url.indexOf('?') == -1)
                    url = url + '?_'+ id + '_sortAlpha=desc';
                else
                    url = url + '&_'+ id + '_sortAlpha=desc';
            }

            if(browserURL.indexOf('_'+ id + '_sortAlpha') != -1)
                browserURL = browserURL.replace('_' + id + '_sortAlpha=asc', '_' + id + '_sortAlpha=desc');
            else {
                if(browserURL.indexOf('?') == -1)
                    browserURL = browserURL + '?_'+ id + '_sortAlpha=desc';
                else
                    browserURL = browserURL + '&_'+ id + '_sortAlpha=desc';
            }

        }
        else {
            var sort = 'asc';

            if(url.indexOf('_'+ id + '_sortAlpha') != -1) {
                url = url.replace('_' + id + '_sortAlpha=desc', '_' + id + '_sortAlpha=asc');
            }
            else {
                if(url.indexOf('?') == -1)
                    url = url + '?_'+ id + '_sortAlpha=asc';
                else
                    url = url + '&_'+ id + '_sortAlpha=asc';
            }

            if(browserURL.indexOf('_'+ id + '_sortAlpha') != -1)
                browserURL = browserURL.replace('_' + id + '_sortAlpha=desc', '_' + id + '_sortAlpha=asc');
            else {
                if(browserURL.indexOf('?') == -1)
                    browserURL = browserURL + '?_'+ id + '_sortAlpha=asc';
                else
                    browserURL = browserURL + '&_'+ id + '_sortAlpha=asc';
            }
        }

        browserURL = browserURL + '#' + id;

        url = url.replace('_' + id + '_sortCnt=asc', '');
        url = url.replace('_' + id + '_sortCnt=desc', '');
        url = url.replace('?&', '?');
        url = url.replace('&&', '&');
        browserURL = browserURL.replace('_' + id + '_sortCnt=asc', '');
        browserURL = browserURL.replace('_' + id + '_sortCnt=desc', '');
        browserURL = browserURL.replace('?&', '?');
        browserURL = browserURL.replace('&&', '&');
		
		if(browserURL.slice(-1) == '&') 
		   browserURL = browserURL.substring(0, browserURL.length - 1);

        $(this).parent().parent().find('p.module-footer a.read-more').attr('href', url);

        if(url.indexOf('_' + id + '_limit=0') == -1) {
            if(url.indexOf('?') == -1)
                url = url + '?_' + id + '_limit=0';
            else
                url = url + '&_' + id + '_limit=0';
        }

        imageChange('alphaSort', id, sort);
        sortFacet(url, id, mylist1, sort, cnt, 'alphaSort');
        window.location.href = browserURL;
    });

    $("img#sortFacetCount").click(function() {

        //get id of current facet
        var id = $(this).parent().parent().find('ul.unstyled.nav.nav-simple.nav-facet').attr('id');
        var url = $(this).parent().parent().find('p.module-footer a.read-more').attr('href');

        if(typeof(url) == 'undefined')
            return;

        var browserURL = window.location.href;

        if(browserURL.indexOf('#') != -1)
            browserURL = browserURL.substring(0, browserURL.indexOf('#'));

        //original list
        var mylist1 = $('ul.unstyled.nav.nav-simple.nav-facet#' + id);
        var cnt = mylist1.children('li').get().length;
        mylist1.html("");

        if(mylist1.hasClass('cnt_asc')) {

            var sort = 'desc';

            if(url.indexOf('_' + id + '_sortCnt') != -1)
                url = url.replace('_' + id + '_sortCnt=asc', '_' + id + '_sortCnt=desc');
            else {
                if(url.indexOf('?') == -1)
                    url = url + '?_'+ id + '_sortCnt=desc';
                else
                    url = url + '&_'+ id + '_sortCnt=desc';
            }

            if(browserURL.indexOf('_'+ id + '_sortCnt') != -1)
                browserURL = browserURL.replace('_' + id + '_sortCnt=asc', '_' + id + '_sortCnt=desc');
            else {
                if(browserURL.indexOf('?') == -1)
                    browserURL = browserURL + '?_'+ id + '_sortCnt=desc';
                else
                    browserURL = browserURL + '&_'+ id + '_sortCnt=desc';
            }

        }
        else {
            var sort = 'asc';

            if(url.indexOf('_'+ id + '_sortCnt') != -1) {
                url = url.replace('_' + id + '_sortCnt=desc', '_' + id + '_sortCnt=asc');
            }
            else {
                if(url.indexOf('?') == -1)
                    url = url + '?_'+ id + '_sortCnt=asc';
                else
                    url = url + '&_'+ id + '_sortCnt=asc';
            }

            if(browserURL.indexOf('_'+ id + '_sortCnt') != -1)
                browserURL = browserURL.replace('_' + id + '_sortCnt=desc', '_' + id + '_sortCnt=asc');
            else {
                if(browserURL.indexOf('?') == -1)
                    browserURL = browserURL + '?_'+ id + '_sortCnt=asc';
                else
                    browserURL = browserURL + '&_'+ id + '_sortCnt=asc';
            }
        }


        url = url.replace('_' + id + '_sortAlpha=asc', '');
        url = url.replace('_' + id + '_sortAlpha=desc', '');
        url = url.replace('?&', '?');
        url = url.replace('&&', '&');
        browserURL = browserURL + '#' + id;
        browserURL = browserURL.replace('_' + id + '_sortAlpha=asc', '');
        browserURL = browserURL.replace('_' + id + '_sortAlpha=desc', '');
        browserURL = browserURL.replace('?&', '?');
        browserURL = browserURL.replace('&&', '&');
		
		if(browserURL.slice(-1) == '&') 
		   browserURL = browserURL.substring(0, browserURL.length - 1);

        $(this).parent().parent().find('p.module-footer a.read-more').attr('href', url);

        if(url.indexOf('_' + id + '_limit=0') == -1) {
            if(url.indexOf('?') == -1)
                url = url + '?_' + id + '_limit=0';
            else
                url = url + '&_' + id + '_limit=0';
        }

        imageChange('countSort', id, sort);
        sortFacet(url, id, mylist1, sort, cnt, 'countSort');

        window.location.href = browserURL;
    });

    function sortFacet(url, id, mylist1, sort, cnt, sortType) {

        $.get(url, function(data,status){

            var mylist = $(data).find('ul.unstyled.nav.nav-simple.nav-facet#' + id);
            var listitems = mylist.children('li').get();

            if(listitems.length == 1) {

                if(sort == 'desc') {
                    //descending sort
                    if(sortType  == 'alphaSort') {
                        mylist1.removeClass('alph_asc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('cnt_desc');
                        mylist1.addClass('alph_desc');
                    }
                    else {
                        mylist1.removeClass('alph_asc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('alph_desc');
                        mylist1.addClass('cnt_desc');
                    }
                }
                else {
                    //ascending sort
                    if(sortType  == 'alphaSort') {
                        mylist1.removeClass('alph_desc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('cnt_desc');
                        mylist1.addClass('alph_asc');
                    }
                    else {
                        mylist1.removeClass('cnt_desc');
                        mylist1.removeClass('alph_desc');
                        mylist1.removeClass('alph_asc');
                        mylist1.addClass('cnt_asc');
                    }
                }

            }

            listitems.sort(function(a, b) {

                if(sortType == 'alphaSort') {
                    var compA = $(a).text().toUpperCase();
                    var compB = $(b).text().toUpperCase();
                }
                else {
                    var compA_arr = $(a).text().split("(");
                    var compB_arr = $(b).text().split("(");
                    var compA = parseInt(compA_arr[compA_arr.length-1].split(')')[0]);
                    var compB = parseInt(compB_arr[compB_arr.length-1].split(')')[0]);

                }

                if(sort == 'desc') {
                    //descending sort
                    if(sortType  == 'alphaSort') {
                        mylist1.removeClass('alph_asc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('cnt_desc');
                        mylist1.addClass('alph_desc');
                    }
                    else {
                        mylist1.removeClass('alph_asc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('alph_desc');
                        mylist1.addClass('cnt_desc');
                    }
                    return (compA > compB) ? -1 : (compA < compB) ? 1 : 0;

                }
                else {
                    //ascending sort
                    if(sortType  == 'alphaSort') {
                        mylist1.removeClass('alph_desc');
                        mylist1.removeClass('cnt_asc');
                        mylist1.removeClass('cnt_desc');
                        mylist1.addClass('alph_asc');
                    }
                    else {
                        mylist1.removeClass('cnt_desc');
                        mylist1.removeClass('alph_desc');
                        mylist1.removeClass('alph_asc');
                        mylist1.addClass('cnt_asc');
                    }

                    return (compA < compB) ? -1 : (compA > compB) ? 1 : 0;

                }
            });

			var read_more_url = $("a[name='sm_" + id + "']").attr('href');
			var flag = false;
			if(read_more_url.indexOf("_" + id + "_limit=0") != -1)
			   flag = true;		   
			
            $.each(listitems, function(idx, itm) {
                if(cnt > 0) {
				    if(flag == true) {
					   var li_url = $(itm).find('a').attr('href');
					   li_url = li_url.replace("_" + id + "_limit=0", "");
					   
					   if(li_url.slice(-1) == '&') 
					      li_url = li_url.substring(0, li_url.length - 1);  
						  
					   $(itm).find('a').attr('href', li_url);
					}
                    mylist1.append(itm);
				}
                cnt--;
            });
        });
    }

    function imageChange(sortType, key, sort) {

        if(sortType == 'alphaSort') {

            $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/fanstatic/geodatagov/images/number.png')

            if(sort == 'desc')
                $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/fanstatic/geodatagov/images/alpha_down.png');
            else
                $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/fanstatic/geodatagov/images/alpha_up.png');

        }

        if(sortType == 'cntSort') {

            $('#' + key).parent().parent().find('img#sortFacetAlpha').attr('src', '/fanstatic/geodatagov/images/alpha.png');

            if(sort == 'desc')
                $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/fanstatic/geodatagov/images/number_down.png');
            else
                $('#' + key).parent().parent().find('img#sortFacetCount').attr('src', '/fanstatic/geodatagov/images/number_up.png');
        }

    }

    /**
     * for all Show more/show less links modify link to take you to that facet
     **/
    $('a#facet_read_more').each( function() {
        var name = $(this).attr('name').split("sm_")[1];
        var url = $(this).attr('href');

        if(url.indexOf('#') == -1)
            $(this).attr('href', url + '#' + name);
    });
});

