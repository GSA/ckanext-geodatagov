if (document.querySelectorAll) {
  var btns = document.querySelectorAll('.close');

  [].forEach.call(btns || [], function (btn) {
    btn.onclick = function () {
      this.parentNode.className = this.parentNode.className.replace('fade-in', '');
      return false;
    };
  });

  window.addEventListener('load', function () {
    var panels = document.querySelectorAll('.module-info-overlay');

    [].forEach.call(panels || [], function (panel) {
      setTimeout(function () {
        panel.className += ' fade-in';
      }, 1500);
    });
  }, false);
}
