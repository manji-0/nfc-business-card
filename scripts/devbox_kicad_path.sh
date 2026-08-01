# Sourced by devbox init_hook — put KiCad App CLI on PATH when present.
# Safe no-op on Linux / when KiCad is not installed under /Applications.

KICAD_APP_MACOS="/Applications/KiCad/KiCad.app/Contents/MacOS"
KICAD_APP_FW="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current"
KICAD_APP_PYTHON="${KICAD_APP_FW}/bin/python3"

if [[ -x "${KICAD_APP_MACOS}/kicad-cli" ]]; then
  case ":${PATH}:" in
    *":${KICAD_APP_MACOS}:"*) ;;
    *) export PATH="${KICAD_APP_MACOS}:${PATH}" ;;
  esac
  export KICAD_CLI="${KICAD_CLI:-${KICAD_APP_MACOS}/kicad-cli}"
fi

if [[ -x "${KICAD_APP_PYTHON}" ]]; then
  export KICAD_PYTHON="${KICAD_PYTHON:-${KICAD_APP_PYTHON}}"
fi

# KiCad 10+: .../lib/python3.X/site-packages ; older: Frameworks/python/site-packages
if [[ -z "${KICAD_SITE:-}" ]]; then
  for candidate in \
    "${KICAD_APP_FW}"/lib/python*/site-packages \
    "/Applications/KiCad/KiCad.app/Contents/Frameworks/python/site-packages"
  do
    if [[ -d "${candidate}" ]]; then
      export KICAD_SITE="${candidate}"
      break
    fi
  done
fi
