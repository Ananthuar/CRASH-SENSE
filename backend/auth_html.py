"""
CrashSense — Browser Auth HTML Templates
==========================================

Dark-themed Firebase JS SDK pages served by the Flask backend.
The desktop app opens these pages in the user's default browser,
waits for the auth to complete, and receives the token via a callback
to a short-lived local HTTP server.
"""

# ─────────────────────────────────────────────────────────────────
#  Shared CSS / Chrome
# ─────────────────────────────────────────────────────────────────

_BASE_STYLE = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0a0a; color: #fff;
    font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
  }
  .card {
    background: #111318; border: 1px solid #1e2028; border-radius: 20px;
    padding: 40px 48px; width: 420px; text-align: center;
  }
  .logo { font-size: 32px; font-weight: 800; color: #f97316; letter-spacing: -1px; }
  .subtitle { color: #6b7280; font-size: 13px; margin-top: 4px; margin-bottom: 32px; }
  .heading { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
  .desc { color: #b0b8c4; font-size: 13px; margin-bottom: 24px; line-height: 1.5; }
  .btn {
    display: block; width: 100%; padding: 14px;
    border: none; border-radius: 12px; cursor: pointer;
    font-size: 15px; font-weight: 600; transition: opacity .15s;
  }
  .btn:hover { opacity: .88; }
  .btn-orange { background: #f97316; color: #fff; }
  .btn-dark   { background: #1a1c24; color: #fff; border: 1px solid #1e2028; }
  .btn-google {
    background: #fff; color: #222; display: flex; align-items: center;
    justify-content: center; gap: 10px; width: 100%; padding: 14px;
    border: none; border-radius: 12px; cursor: pointer;
    font-size: 15px; font-weight: 600; transition: opacity .15s;
  }
  .btn-google:hover { opacity: .9; }
  .input {
    width: 100%; padding: 12px 16px; background: #0a0c10;
    border: 1px solid #1e2028; border-radius: 10px;
    color: #fff; font-size: 14px; outline: none;
    margin-bottom: 12px;
  }
  .input:focus { border-color: #f97316; }
  .input::placeholder { color: #6b7280; }
  .label { text-align: left; font-size: 12px; color: #b0b8c4; margin-bottom: 6px; }
  .divider { border: none; border-top: 1px solid #1e2028; margin: 24px 0; }
  .error { color: #ef4444; font-size: 13px; margin: 12px 0; min-height: 20px; }
  .success { color: #22c55e; font-size: 13px; margin: 12px 0; }
  .step { color: #6b7280; font-size: 12px; margin-top: 16px; }
  .spinner {
    display: inline-block; width: 20px; height: 20px;
    border: 2px solid #f97316; border-top-color: transparent;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  #loading { display: none; }
</style>
"""

_FIREBASE_CDN = """
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
"""

# ─────────────────────────────────────────────────────────────────
#  Google Auth HTML
# ─────────────────────────────────────────────────────────────────

GOOGLE_AUTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CrashSense — Sign in with Google</title>
  """ + _BASE_STYLE + _FIREBASE_CDN + """
</head>
<body>
<div class="card">
  <div class="logo">CS</div>
  <div class="subtitle">CRASH SENSE &mdash; AI Crash Detection</div>

  <div class="heading">Sign in with Google</div>
  <div class="desc">Your Google account will be used to securely authenticate you.<br>Click the button below to continue.</div>

  <div id="error" class="error"></div>
  <div id="loading" style="display:none; margin-bottom:16px;">
    <span class="spinner"></span>Signing you in&hellip;
  </div>

  <button class="btn-google" id="googleBtn" onclick="doGoogleSignIn()">
    <svg width="20" height="20" viewBox="0 0 48 48">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.7 2.4 30.2 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.8 6C12.4 13 17.8 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"/>
      <path fill="#FBBC05" d="M10.5 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6A23.9 23.9 0 0 0 0 24c0 3.9.9 7.5 2.5 10.7l8-6z"/>
      <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.5-5.8c-2.1 1.4-4.7 2.3-7.7 2.3-6.2 0-11.5-4.2-13.4-9.8l-8 6.2C6.5 42.5 14.6 48 24 48z"/>
    </svg>
    Continue with Google
  </button>

  <div class="step">A popup will appear. If blocked, allow popups for this site.</div>
</div>

<script>
  const cfg = {
    apiKey:      "{{ api_key }}",
    authDomain:  "{{ auth_domain }}",
    projectId:   "{{ project_id }}"
  };
  const CALLBACK = "{{ callback_url }}";

  firebase.initializeApp(cfg);
  const auth = firebase.auth();

  function showError(msg) {
    document.getElementById('error').textContent = msg;
    document.getElementById('loading').style.display = 'none';
    document.getElementById('googleBtn').style.display = 'block';
  }

  async function doGoogleSignIn() {
    document.getElementById('googleBtn').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').textContent = '';
    const provider = new firebase.auth.GoogleAuthProvider();
    try {
      const result = await auth.signInWithPopup(provider);
      const idToken = await result.user.getIdToken();
      const params = new URLSearchParams({
        uid:          result.user.uid,
        id_token:     idToken,
        email:        result.user.email || '',
        display_name: result.user.displayName || '',
      });
      window.location.href = CALLBACK + '?' + params.toString();
    } catch (err) {
      if (err.code === 'auth/popup-blocked') {
        showError('Popup was blocked by your browser. Please allow popups for localhost:5000 and try again.');
      } else {
        showError(err.message || 'Google Sign-In failed.');
      }
    }
  }
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────
#  Phone Auth HTML
# ─────────────────────────────────────────────────────────────────

PHONE_AUTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CrashSense — Phone Sign-In</title>
  """ + _BASE_STYLE + _FIREBASE_CDN + """
</head>
<body>
<div class="card">
  <div class="logo">CS</div>
  <div class="subtitle">CRASH SENSE &mdash; AI Crash Detection</div>

  <!-- Step 1: Phone Number -->
  <div id="step1">
    <div class="heading">Phone Number Sign-In</div>
    <div class="desc">Enter your phone number with country code (e.g. +91 9876543210).</div>
    <div id="errorStep1" class="error"></div>

    <div class="label">Phone Number</div>
    <input id="phoneInput" class="input" type="tel" placeholder="+91 9876543210">

    <button class="btn btn-orange" id="sendBtn" onclick="sendOtp()" style="margin-top:4px;">
      Send Verification Code
    </button>
    <div id="loadStep1" style="display:none; margin-top:12px;">
      <span class="spinner"></span>Sending OTP&hellip;
    </div>

    <!-- Invisible reCAPTCHA container -->
    <div id="recaptcha-container"></div>
  </div>

  <!-- Step 2: OTP verification -->
  <div id="step2" style="display:none;">
    <div class="heading">Enter Verification Code</div>
    <div class="desc" id="step2Desc">We sent a 6-digit code to your phone.</div>
    <div id="errorStep2" class="error"></div>

    <div class="label">6-Digit Code</div>
    <input id="otpInput" class="input" type="text" placeholder="123456" maxlength="6">

    <button class="btn btn-orange" onclick="verifyOtp()" style="margin-top:4px;">
      Verify Code
    </button>
    <button class="btn btn-dark" onclick="resetToStep1()" style="margin-top:8px;">
      &larr; Change Number
    </button>
    <div id="loadStep2" style="display:none; margin-top:12px;">
      <span class="spinner"></span>Verifying&hellip;
    </div>
  </div>
</div>

<script>
  const cfg = {
    apiKey:      "{{ api_key }}",
    authDomain:  "{{ auth_domain }}",
    projectId:   "{{ project_id }}"
  };
  const CALLBACK = "{{ callback_url }}";

  firebase.initializeApp(cfg);
  const auth = firebase.auth();
  let confirmationResult = null;
  let recaptchaVerifier = null;

  function initRecaptcha() {
    recaptchaVerifier = new firebase.auth.RecaptchaVerifier('recaptcha-container', {
      'size': 'invisible',
      'callback': () => {}
    });
  }

  window.onload = initRecaptcha;

  async function sendOtp() {
    const phone = document.getElementById('phoneInput').value.trim();
    if (!phone.startsWith('+')) {
      document.getElementById('errorStep1').textContent = 'Include country code, e.g. +91 9876543210';
      return;
    }
    document.getElementById('sendBtn').style.display = 'none';
    document.getElementById('loadStep1').style.display = 'block';
    document.getElementById('errorStep1').textContent = '';
    try {
      confirmationResult = await auth.signInWithPhoneNumber(phone, recaptchaVerifier);
      document.getElementById('step2Desc').textContent = 'We sent a 6-digit code to ' + phone;
      document.getElementById('step1').style.display = 'none';
      document.getElementById('step2').style.display = 'block';
    } catch (err) {
      document.getElementById('sendBtn').style.display = 'block';
      document.getElementById('loadStep1').style.display = 'none';
      document.getElementById('errorStep1').textContent = err.message || 'Failed to send OTP.';
      // Re-init recaptcha after failure
      recaptchaVerifier.clear();
      initRecaptcha();
    }
  }

  async function verifyOtp() {
    const code = document.getElementById('otpInput').value.trim();
    if (code.length !== 6) {
      document.getElementById('errorStep2').textContent = 'Please enter the 6-digit code.';
      return;
    }
    document.getElementById('loadStep2').style.display = 'block';
    document.getElementById('errorStep2').textContent = '';
    try {
      const result = await confirmationResult.confirm(code);
      const idToken = await result.user.getIdToken();
      const params = new URLSearchParams({
        uid:          result.user.uid,
        id_token:     idToken,
        email:        result.user.email || '',
        display_name: result.user.displayName || '',
      });
      window.location.href = CALLBACK + '?' + params.toString();
    } catch (err) {
      document.getElementById('loadStep2').style.display = 'none';
      document.getElementById('errorStep2').textContent = err.message || 'Invalid code. Please try again.';
    }
  }

  function resetToStep1() {
    document.getElementById('step1').style.display = 'block';
    document.getElementById('step2').style.display = 'none';
    document.getElementById('sendBtn').style.display = 'block';
    document.getElementById('loadStep1').style.display = 'none';
    document.getElementById('otpInput').value = '';
    document.getElementById('errorStep2').textContent = '';
    recaptchaVerifier.clear();
    initRecaptcha();
  }
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────
#  Email Link (Passwordless) Auth HTML
# ─────────────────────────────────────────────────────────────────

EMAIL_LINK_AUTH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CrashSense — Email Sign-In</title>
  """ + _BASE_STYLE + _FIREBASE_CDN + """
</head>
<body>
<div class="card">
  <div class="logo">CS</div>
  <div class="subtitle">CRASH SENSE &mdash; AI Crash Detection</div>

  <!-- State 1: Enter email -->
  <div id="emailForm">
    <div class="heading">Email Sign-In</div>
    <div class="desc">We'll send a sign-in link to your email via Firebase.<br>Click it to authenticate &mdash; no password needed.</div>
    <div id="error" class="error"></div>

    <div class="label">Email Address</div>
    <input id="emailInput" class="input" type="email" placeholder="you@example.com">

    <button class="btn btn-orange" id="sendBtn" onclick="sendLink()" style="margin-top:4px;">
      Send Sign-In Link
    </button>
    <div id="loading" style="display:none; margin-top:12px;">
      <span class="spinner"></span>Sending link&hellip;
    </div>
  </div>

  <!-- State 2: Link sent confirmation -->
  <div id="sentMsg" style="display:none;">
    <div class="heading">&#10003; Check Your Inbox</div>
    <div class="desc" id="sentDesc">We sent a sign-in link. Click it to continue.</div>
    <div class="step">Waiting for you to click the link&hellip;</div>
    <button class="btn btn-dark" onclick="resetForm()" style="margin-top:16px;">
      &larr; Try a Different Email
    </button>
  </div>

  <!-- State 3: Completing sign-in (from link click) -->
  <div id="completing" style="display:none;">
    <div class="heading">Signing You In&hellip;</div>
    <div id="completingError" class="error"></div>
    <div id="completingLoad" style="margin-top:12px;">
      <span class="spinner"></span>Almost there&hellip;
    </div>
  </div>
</div>

<script>
  const cfg = {
    apiKey:      "{{ api_key }}",
    authDomain:  "{{ auth_domain }}",
    projectId:   "{{ project_id }}"
  };
  const CALLBACK = "{{ callback_url }}";

  firebase.initializeApp(cfg);
  const auth = firebase.auth();

  // On page load: check if this IS the sign-in link click
  window.onload = function() {
    if (firebase.auth.isSignInWithEmailLink(auth, window.location.href)) {
      completeSignIn();
    }
  };

  async function sendLink() {
    const email = document.getElementById('emailInput').value.trim();
    if (!email) {
      document.getElementById('error').textContent = 'Please enter your email.';
      return;
    }
    document.getElementById('sendBtn').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').textContent = '';

    const actionCodeSettings = {
      url: window.location.href,
      handleCodeInApp: true,
    };

    try {
      await firebase.auth().sendSignInLinkToEmail(email, actionCodeSettings);
      window.localStorage.setItem('crashsenseEmail', email);
      document.getElementById('emailForm').style.display = 'none';
      document.getElementById('sentDesc').textContent =
        'We sent a sign-in link to ' + email + '. Open your email and click the link.';
      document.getElementById('sentMsg').style.display = 'block';
    } catch (err) {
      document.getElementById('sendBtn').style.display = 'block';
      document.getElementById('loading').style.display = 'none';
      document.getElementById('error').textContent = err.message || 'Failed to send link.';
    }
  }

  async function completeSignIn() {
    document.getElementById('emailForm').style.display = 'none';
    document.getElementById('sentMsg').style.display = 'none';
    document.getElementById('completing').style.display = 'block';

    let email = window.localStorage.getItem('crashsenseEmail');
    if (!email) {
      email = window.prompt('Please enter your email to confirm sign-in:');
    }
    if (!email) {
      document.getElementById('completingError').textContent = 'Email is required.';
      document.getElementById('completingLoad').style.display = 'none';
      return;
    }

    try {
      const result = await firebase.auth().signInWithEmailLink(email, window.location.href);
      window.localStorage.removeItem('crashsenseEmail');
      const idToken = await result.user.getIdToken();
      const params = new URLSearchParams({
        uid:          result.user.uid,
        id_token:     idToken,
        email:        result.user.email || email,
        display_name: result.user.displayName || email.split('@')[0],
      });
      window.location.href = CALLBACK + '?' + params.toString();
    } catch (err) {
      document.getElementById('completingLoad').style.display = 'none';
      document.getElementById('completingError').textContent =
        err.message || 'Sign-in failed. Please try again.';
    }
  }

  function resetForm() {
    document.getElementById('sentMsg').style.display = 'none';
    document.getElementById('emailForm').style.display = 'block';
    document.getElementById('sendBtn').style.display = 'block';
    document.getElementById('loading').style.display = 'none';
  }
</script>
</body>
</html>"""
