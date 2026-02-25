<!DOCTYPE html>
<html>
<body>
<video autoplay playsinline></video>
<script>
navigator.mediaDevices.getUserMedia({ video: true, audio: false })
  .then(stream => { document.querySelector('video').srcObject = stream; })
  .catch(err => alert('Erreur caméra: ' + err.message));
</script>
</body>
</html>