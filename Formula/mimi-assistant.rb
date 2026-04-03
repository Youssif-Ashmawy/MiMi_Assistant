class MimiAssistant < Formula
  desc "Voice-activated gesture recognition assistant for macOS"
  homepage "https://github.com/youssif/MiMi_Assistant"

  # Update url + sha256 each release:
  #   url  → https://github.com/youssif/MiMi_Assistant/archive/refs/tags/vX.Y.Z.tar.gz
  #   sha256 → run: curl -sL <url> | shasum -a 256
  url "https://github.com/youssif/MiMi_Assistant/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "Apache-2.0"

  depends_on :macos
  depends_on "portaudio" # required by pyaudio

  def install
    # Install source code and models
    libexec.install "src", "models", "scripts"
    libexec.install "requirements.txt"

    # Create venv and install Python deps
    venv = libexec/"venv"
    system "python3", "-m", "venv", venv.to_s
    system "#{venv}/bin/pip", "install", "--upgrade", "pip", "--quiet"
    system "#{venv}/bin/pip", "install", "-r", "#{libexec}/requirements.txt", "--quiet"

    # bin/mimi-assistant — starts the assistant
    (bin/"mimi-assistant").write <<~SH
      #!/bin/bash
      export MIMI_HOME="#{libexec}"
      export MIMI_LOGS="$HOME/.mimi/logs"
      mkdir -p "$MIMI_LOGS"
      exec "#{libexec}/venv/bin/python" "#{libexec}/src/main.py" "$@"
    SH

    # bin/mimi-ctl — control script (start/stop/restart/status/logs)
    (bin/"mimi-ctl").write <<~SH
      #!/bin/bash
      export MIMI_HOME="#{libexec}"
      export MIMI_LOGS="$HOME/.mimi/logs"
      exec "#{libexec}/scripts/mimi-ctl.sh" "$@"
    SH

    # bin/mimi-setup — adds auto-start to ~/.zprofile (run once after install)
    (bin/"mimi-setup").write <<~SH
      #!/bin/bash
      export MIMI_HOME="#{libexec}"
      export MIMI_LOGS="$HOME/.mimi/logs"
      exec "#{libexec}/scripts/mimi-setup.sh" "$@"
    SH

    chmod 0755, bin/"mimi-assistant"
    chmod 0755, bin/"mimi-ctl"
    chmod 0755, bin/"mimi-setup"
  end

  def caveats
    <<~EOS
      Run the one-time setup to enable auto-start on Terminal open:
        mimi-setup

      Then start immediately with:
        mimi-ctl start

      ⚠️  Terminal must have Microphone permission:
        System Settings → Privacy & Security → Microphone → Terminal ✓
    EOS
  end

  test do
    assert_match "Usage", shell_output("#{bin}/mimi-ctl 2>&1", 1)
  end
end
