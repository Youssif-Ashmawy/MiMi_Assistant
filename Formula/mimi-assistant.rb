class MimiAssistant < Formula
  desc "Voice-activated gesture recognition assistant for macOS"
  homepage "https://github.com/Youssif-Ashmawy/MiMi_Assistant"

  # Update url + sha256 each release:
  #   url  → https://github.com/Youssif-Ashmawy/MiMi_Assistant/archive/refs/tags/vX.Y.Z.tar.gz
  #   sha256 → run: curl -sL <url> | shasum -a 256
  url "https://github.com/Youssif-Ashmawy/MiMi_Assistant/archive/refs/tags/v1.0.9.tar.gz"
  sha256 "3e4d8d559599b94be4145b86aba21817de4b41df5707f48303c83467347a11e7"
  license "Apache-2.0"

  depends_on :macos
  depends_on "python@3.13"
  depends_on "portaudio" # required by pyaudio

  def install
    # Install all project files preserving directory structure
    (libexec/"src").install Dir["src/*"]
    (libexec/"models").install Dir["models/*"]
    (libexec/"scripts").install Dir["scripts/*"]
    libexec.install "requirements.txt"

    # Create venv using the Homebrew Python 3.13 explicitly
    python = Formula["python@3.13"].opt_bin/"python3.13"
    venv = libexec/"venv"
    system python, "-m", "venv", venv.to_s
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

      Other commands:
        mimi-ctl stop        — stop MiMi
        mimi-ctl status      — check if running
        mimi-ctl logs        — live log tail
        mimi-ctl upgrade     — upgrade to latest version
        mimi-ctl uninstall   — fully uninstall MiMi

      ⚠️  Terminal must have Microphone permission:
        System Settings → Privacy & Security → Microphone → Terminal ✓
    EOS
  end

  test do
    assert_match "Usage", shell_output("#{bin}/mimi-ctl 2>&1", 1)
  end
end
