/**
 * video.js
 * Detects each .md-video element's natural dimensions once metadata loads
 * and adds "portrait" or "landscape" to the parent <figure>.
 * CSS then sizes portrait videos as a narrow centered column and
 * landscape videos full-width.
 */
(function () {
  "use strict";

  function applyOrientation(video) {
    var figure = video.closest(".md-video");
    if (!figure || !video.videoWidth || !video.videoHeight) return;
    figure.classList.add(video.videoWidth <= video.videoHeight ? "portrait" : "landscape");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".md-video video").forEach(function (video) {
      if (video.readyState >= 1) {
        applyOrientation(video);
      } else {
        video.addEventListener("loadedmetadata", function () {
          applyOrientation(video);
        });
      }
    });
  });
}());