import React, { useState, useEffect, useRef, useCallback } from "react";
import { getStepsForRole } from "./tutorialSteps";

/**
 * Lightweight Web Audio API Synthesizer for high-tech UI sound effects
 */
class SoundEffects {
  constructor() {
    this.ctx = null;
    this.muted = localStorage.getItem("landnexus_tour_muted") === "true";
  }

  init() {
    if (!this.ctx && typeof window !== "undefined") {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  setMuted(val) {
    this.muted = val;
    localStorage.setItem("landnexus_tour_muted", val ? "true" : "false");
  }

  playStep() {
    if (this.muted) return;
    try {
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      const now = this.ctx.currentTime;
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(740, now + 0.1);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.12);
    } catch (_) {}
  }

  playBack() {
    if (this.muted) return;
    try {
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      const now = this.ctx.currentTime;
      osc.frequency.setValueAtTime(660, now);
      osc.frequency.exponentialRampToValueAtTime(440, now + 0.1);
      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.1);
    } catch (_) {}
  }

  playCelebrate() {
    if (this.muted) return;
    try {
      this.init();
      if (!this.ctx) return;
      const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6
      notes.forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "triangle";
        const startTime = this.ctx.currentTime + idx * 0.09;
        osc.frequency.setValueAtTime(freq, startTime);
        gain.gain.setValueAtTime(0.1, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.28);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + 0.3);
      });
    } catch (_) {}
  }
}

const sfx = new SoundEffects();

/**
 * Confetti Canvas animation for Tour Completion
 */
function ConfettiCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const colors = ["#06b6d4", "#38bdf8", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#fbbf24"];
    const particles = Array.from({ length: 90 }).map(() => ({
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 100,
      vx: (Math.random() - 0.5) * 14,
      vy: (Math.random() - 0.8) * 16,
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      vRot: (Math.random() - 0.5) * 10,
      opacity: 1
    }));

    let animId;
    function render() {
      ctx.clearRect(0, 0, width, height);
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.35; // gravity
        p.vx *= 0.98;
        p.rotation += p.vRot;
        p.opacity -= 0.004;

        if (p.opacity > 0) {
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate((p.rotation * Math.PI) / 180);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = Math.max(0, p.opacity);
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.7);
          ctx.restore();
        }
      });
      animId = requestAnimationFrame(render);
    }
    render();

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        pointerEvents: "none",
        zIndex: 99999
      }}
    />
  );
}

/**
 * Main Interactive Tutorial Component
 */
export default function TutorialEngine({
  user,
  currentPage,
  onNavigate,
  isOpen,
  onClose
}) {
  const [steps, setSteps] = useState([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [muted, setMuted] = useState(sfx.muted);
  const [isSearching, setIsSearching] = useState(false);
  const retryTimerRef = useRef(null);

  // Initialize steps based on active user role
  useEffect(() => {
    if (!user) return;
    const roleSteps = getStepsForRole(user.role);
    setSteps(roleSteps);
    setStepIndex(0);
    setIsCompleted(false);
  }, [user]);

  const currentStep = steps[stepIndex] || null;

  // Toggle Mute
  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    sfx.setMuted(next);
  };

  // Locate and measure target DOM element
  const updateTargetPosition = useCallback(() => {
    if (!isOpen || !currentStep) return;

    // Check if step requires a specific page
    if (currentStep.targetPage && currentPage !== currentStep.targetPage && onNavigate) {
      onNavigate(currentStep.targetPage);
    }

    let attempts = 0;
    const maxAttempts = 12;

    const findTarget = () => {
      const el = document.querySelector(currentStep.selector);
      if (el) {
        const rect = el.getBoundingClientRect();
        // Check if element is rendered and has size
        if (rect.width > 0 && rect.height > 0) {
          // Scroll into view if outside visible viewport
          const inView =
            rect.top >= 60 &&
            rect.left >= 0 &&
            rect.bottom <= window.innerHeight - 60 &&
            rect.right <= window.innerWidth;

          if (!inView) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            // Re-read rect after smooth scroll settles
            setTimeout(() => {
              const updated = el.getBoundingClientRect();
              setTargetRect({
                top: updated.top,
                left: updated.left,
                width: updated.width,
                height: updated.height,
                radius: window.getComputedStyle(el).borderRadius || "8px"
              });
              setIsSearching(false);
            }, 300);
            return;
          }

          setTargetRect({
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            radius: window.getComputedStyle(el).borderRadius || "8px"
          });
          setIsSearching(false);
          return;
        }
      }

      attempts++;
      if (attempts < maxAttempts) {
        setIsSearching(true);
        retryTimerRef.current = setTimeout(findTarget, 150);
      } else {
        // Fallback: Centered spotlight if element isn't in DOM
        setIsSearching(false);
        setTargetRect(null);
      }
    };

    findTarget();
  }, [isOpen, currentStep, currentPage, onNavigate]);

  // Trigger position recalculation on step change, resize, and scroll
  useEffect(() => {
    if (!isOpen || isCompleted) return;

    clearTimeout(retryTimerRef.current);
    updateTargetPosition();

    const handleWindowChange = () => {
      updateTargetPosition();
    };

    window.addEventListener("resize", handleWindowChange);
    window.addEventListener("scroll", handleWindowChange, true);

    return () => {
      clearTimeout(retryTimerRef.current);
      window.removeEventListener("resize", handleWindowChange);
      window.removeEventListener("scroll", handleWindowChange, true);
    };
  }, [stepIndex, isOpen, isCompleted, updateTargetPosition]);

  // Keyboard Navigation: Enter/Right -> next, Left -> back, Esc -> close
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = e => {
      if (e.key === "Escape") {
        handleSkip();
      } else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        handleNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        handleBack();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const handleNext = () => {
    if (stepIndex < steps.length - 1) {
      sfx.playStep();
      setStepIndex(prev => prev + 1);
    } else {
      // Tour Completed!
      sfx.playCelebrate();
      setIsCompleted(true);
      localStorage.setItem("landnexus_tour_completed", "true");
    }
  };

  const handleBack = () => {
    if (stepIndex > 0) {
      sfx.playBack();
      setStepIndex(prev => prev - 1);
    }
  };

  const handleSkip = () => {
    localStorage.setItem("landnexus_tour_completed", "true");
    if (onClose) onClose();
  };

  const handleFinish = () => {
    localStorage.setItem("landnexus_tour_completed", "true");
    if (onClose) onClose();
  };

  if (!isOpen) return null;

  // Render Completion Celebration Modal
  if (isCompleted) {
    return (
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          background: "rgba(15, 23, 42, 0.85)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 99998,
          padding: "20px"
        }}
      >
        <ConfettiCanvas />
        <div
          style={{
            background: "linear-gradient(145deg, #0f172a 0%, #1e293b 100%)",
            border: "2px solid #06b6d4",
            boxShadow: "0 0 40px rgba(6, 182, 212, 0.45), 0 20px 40px rgba(0,0,0,0.6)",
            borderRadius: "16px",
            maxWidth: "520px",
            width: "100%",
            color: "#f8fafc",
            padding: "32px 28px",
            textAlign: "center",
            position: "relative",
            zIndex: 99999,
            animation: "landnexusModalPop 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275)"
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "72px",
              height: "72px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #06b6d4 0%, #0284c7 100%)",
              fontSize: "36px",
              marginBottom: "16px",
              boxShadow: "0 0 24px rgba(6, 182, 212, 0.6)"
            }}
          >
            🏆
          </div>

          <div
            style={{
              fontSize: "11px",
              fontWeight: 800,
              color: "#38bdf8",
              letterSpacing: "1.5px",
              textTransform: "uppercase",
              marginBottom: "6px"
            }}
          >
            MISSION COMPLETE
          </div>

          <h2 style={{ margin: "0 0 10px 0", fontSize: "24px", fontWeight: 800, color: "#ffffff" }}>
            You're Ready to Command LandNexus!
          </h2>

          <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: 1.6, margin: "0 0 22px 0" }}>
            You've completed the interactive onboarding tour for{" "}
            <b style={{ color: "#38bdf8" }}>
              {(user?.role || "Official").replace("_", " ").toUpperCase()}
            </b>
            . You have unlocked operational proficiency across:
          </p>

          <div
            style={{
              display: "grid",
              gap: "10px",
              textAlign: "left",
              marginBottom: "26px",
              background: "rgba(15, 23, 42, 0.6)",
              padding: "16px",
              borderRadius: "10px",
              border: "1px solid rgba(56, 189, 248, 0.2)"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
              <span style={{ color: "#10b981", fontSize: "16px" }}>✓</span>
              <span>
                <b>Geospatial Cadastral Engine:</b> High-resolution FMB boundary & satellite alignment
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
              <span style={{ color: "#06b6d4", fontSize: "16px" }}>✓</span>
              <span>
                <b>AI Decision Support (RB-DSS):</b> Deterministic risk scores & early warning radar
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "13px" }}>
              <span style={{ color: "#f59e0b", fontSize: "16px" }}>✓</span>
              <span>
                <b>Statutory Timeline Governance:</b> RFCTLARR SLA monitoring & grievance redressal
              </span>
            </div>
          </div>

          <button
            onClick={handleFinish}
            style={{
              width: "100%",
              padding: "12px 24px",
              background: "linear-gradient(135deg, #06b6d4 0%, #0284c7 100%)",
              color: "#ffffff",
              border: "none",
              borderRadius: "8px",
              fontWeight: 800,
              fontSize: "15px",
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(6, 182, 212, 0.4)",
              transition: "transform 0.15s ease, box-shadow 0.15s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px"
            }}
            onMouseOver={e => (e.currentTarget.style.transform = "scale(1.02)")}
            onMouseOut={e => (e.currentTarget.style.transform = "scale(1)")}
          >
            <span>Start Exploring LandNexus</span>
            <span>🚀</span>
          </button>
        </div>
      </div>
    );
  }

  if (!currentStep) return null;

  // Calculate Tooltip Position relative to Target Rect
  const pad = currentStep.spotlightPadding || 8;
  const targetX = targetRect ? targetRect.left - pad : window.innerWidth / 2;
  const targetY = targetRect ? targetRect.top - pad : window.innerHeight / 2;
  const targetW = targetRect ? targetRect.width + pad * 2 : 0;
  const targetH = targetRect ? targetRect.height + pad * 2 : 0;

  // Determine optimal card placement
  let cardTop = 0;
  let cardLeft = 0;
  let arrowDir = "top"; // arrow points from card towards target
  const cardWidth = 380;
  const cardHeight = 240;

  if (targetRect) {
    const pos = currentStep.position || "bottom";

    if (pos === "bottom") {
      cardTop = targetY + targetH + 16;
      cardLeft = targetX + targetW / 2 - cardWidth / 2;
      arrowDir = "top";
      // Overflow clamp bottom
      if (cardTop + cardHeight > window.innerHeight - 20) {
        cardTop = targetY - cardHeight - 16;
        arrowDir = "bottom";
      }
    } else if (pos === "top") {
      cardTop = targetY - cardHeight - 16;
      cardLeft = targetX + targetW / 2 - cardWidth / 2;
      arrowDir = "bottom";
      // Overflow clamp top
      if (cardTop < 20) {
        cardTop = targetY + targetH + 16;
        arrowDir = "top";
      }
    } else if (pos === "right") {
      cardTop = targetY + targetH / 2 - cardHeight / 2;
      cardLeft = targetX + targetW + 18;
      arrowDir = "left";
      // Overflow clamp right
      if (cardLeft + cardWidth > window.innerWidth - 20) {
        cardLeft = targetX - cardWidth - 18;
        arrowDir = "right";
      }
    } else if (pos === "left") {
      cardTop = targetY + targetH / 2 - cardHeight / 2;
      cardLeft = targetX - cardWidth - 18;
      arrowDir = "right";
      // Overflow clamp left
      if (cardLeft < 20) {
        cardLeft = targetX + targetW + 18;
        arrowDir = "left";
      }
    }

    // Horizontal viewport clamp
    if (cardLeft < 20) cardLeft = 20;
    if (cardLeft + cardWidth > window.innerWidth - 20) {
      cardLeft = window.innerWidth - cardWidth - 20;
    }

    // Vertical viewport clamp
    if (cardTop < 20) cardTop = 20;
    if (cardTop + cardHeight > window.innerHeight - 20) {
      cardTop = window.innerHeight - cardHeight - 20;
    }
  } else {
    // Center fallback
    cardTop = window.innerHeight / 2 - cardHeight / 2;
    cardLeft = window.innerWidth / 2 - cardWidth / 2;
    arrowDir = "none";
  }

  // Pointer Hand Coordinates
  let pointerTop = 0;
  let pointerLeft = 0;
  let pointerEmoji = "👉";

  if (targetRect) {
    if (arrowDir === "top") {
      pointerTop = targetY + targetH + 2;
      pointerLeft = targetX + targetW / 2 - 14;
      pointerEmoji = "👆";
    } else if (arrowDir === "bottom") {
      pointerTop = targetY - 32;
      pointerLeft = targetX + targetW / 2 - 14;
      pointerEmoji = "👇";
    } else if (arrowDir === "left") {
      pointerTop = targetY + targetH / 2 - 16;
      pointerLeft = targetX + targetW + 2;
      pointerEmoji = "👈";
    } else if (arrowDir === "right") {
      pointerTop = targetY + targetH / 2 - 16;
      pointerLeft = targetX - 32;
      pointerEmoji = "👉";
    }
  }

  const progressPercent = ((stepIndex + 1) / steps.length) * 100;

  return (
    <>
      <style>{`
        @keyframes landnexusPulseRing {
          0% { box-shadow: 0 0 0 3px #06b6d4, 0 0 15px rgba(6, 182, 212, 0.6); }
          50% { box-shadow: 0 0 0 5px #38bdf8, 0 0 30px rgba(56, 189, 248, 0.9); }
          100% { box-shadow: 0 0 0 3px #06b6d4, 0 0 15px rgba(6, 182, 212, 0.6); }
        }
        @keyframes landnexusBob {
          0%, 100% { transform: translateY(0px) scale(1); }
          50% { transform: translateY(-8px) scale(1.1); }
        }
        @keyframes landnexusModalPop {
          0% { opacity: 0; transform: scale(0.92) translateY(10px); }
          100% { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>

      {/* ── SVG Spotlight Mask (Darkens entire screen except the highlighted target box) ── */}
      <svg
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          zIndex: 99990,
          pointerEvents: "auto",
          transition: "all 0.25s ease-out"
        }}
        onClick={e => {
          // Allow clicking on backdrop to advance or prevent misclick
          e.stopPropagation();
        }}
      >
        <defs>
          <mask id="landnexus-spotlight-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {targetRect && (
              <rect
                x={targetX}
                y={targetY}
                width={targetW}
                height={targetH}
                rx={10}
                ry={10}
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(15, 23, 42, 0.76)"
          mask="url(#landnexus-spotlight-mask)"
        />
      </svg>

      {/* ── Pulsing Glowing Border Ring over the Highlighted Target ── */}
      {targetRect && (
        <div
          style={{
            position: "fixed",
            top: targetY,
            left: targetX,
            width: targetW,
            height: targetH,
            borderRadius: "10px",
            border: "2px solid #06b6d4",
            animation: "landnexusPulseRing 2s infinite ease-in-out",
            zIndex: 99992,
            pointerEvents: "none",
            transition: "all 0.25s cubic-bezier(0.2, 0.9, 0.3, 1)"
          }}
        />
      )}

      {/* ── Animated Floating Pointer Hand / Indicator ── */}
      {targetRect && arrowDir !== "none" && (
        <div
          style={{
            position: "fixed",
            top: pointerTop,
            left: pointerLeft,
            fontSize: "26px",
            zIndex: 99995,
            pointerEvents: "none",
            animation: "landnexusBob 1.6s infinite ease-in-out",
            filter: "drop-shadow(0 0 8px rgba(6, 182, 212, 0.8))"
          }}
        >
          {pointerEmoji}
        </div>
      )}

      {/* ── Game-Style HUD Tooltip Card ── */}
      <div
        style={{
          position: "fixed",
          top: cardTop,
          left: cardLeft,
          width: `${cardWidth}px`,
          zIndex: 99996,
          background: "linear-gradient(145deg, rgba(15, 23, 42, 0.96) 0%, rgba(30, 41, 59, 0.96) 100%)",
          border: "1px solid rgba(56, 189, 248, 0.4)",
          boxShadow: "0 16px 36px rgba(0, 0, 0, 0.5), 0 0 20px rgba(6, 182, 212, 0.25)",
          backdropFilter: "blur(12px)",
          borderRadius: "14px",
          color: "#f8fafc",
          overflow: "hidden",
          transition: "all 0.25s cubic-bezier(0.2, 0.9, 0.3, 1)",
          animation: "landnexusModalPop 0.22s ease-out"
        }}
      >
        {/* Glowing Top Progress Bar */}
        <div style={{ height: "3px", width: "100%", background: "rgba(255, 255, 255, 0.1)" }}>
          <div
            style={{
              height: "100%",
              width: `${progressPercent}%`,
              background: "linear-gradient(90deg, #06b6d4 0%, #38bdf8 100%)",
              boxShadow: "0 0 8px #38bdf8",
              transition: "width 0.3s ease"
            }}
          />
        </div>

        {/* Card Header */}
        <div
          style={{
            padding: "12px 16px 8px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "14px" }}>🎮</span>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 800,
                letterSpacing: "1px",
                color: "#38bdf8",
                textTransform: "uppercase"
              }}
            >
              {currentStep.badge || "GUIDED TOUR"}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {/* Audio Toggle */}
            <button
              type="button"
              onClick={toggleMute}
              title={muted ? "Unmute Audio Effects" : "Mute Audio Effects"}
              style={{
                background: "transparent",
                border: "none",
                color: muted ? "#64748b" : "#38bdf8",
                cursor: "pointer",
                fontSize: "14px",
                padding: "2px 4px"
              }}
            >
              {muted ? "🔇" : "🔊"}
            </button>

            {/* Step Counter Badge */}
            <span
              style={{
                fontSize: "10px",
                fontWeight: 800,
                color: "#e2e8f0",
                background: "rgba(255, 255, 255, 0.12)",
                padding: "3px 8px",
                borderRadius: "10px"
              }}
            >
              {stepIndex + 1} / {steps.length}
            </span>

            {/* Skip / Close */}
            <button
              type="button"
              onClick={handleSkip}
              title="Skip Tour"
              style={{
                background: "transparent",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: "16px",
                lineHeight: 1,
                padding: "2px 4px"
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Card Body */}
        <div style={{ padding: "14px 16px" }}>
          <h3
            style={{
              margin: "0 0 8px 0",
              fontSize: "15px",
              fontWeight: 800,
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            {currentStep.title}
          </h3>

          <p
            style={{
              margin: "0 0 12px 0",
              fontSize: "13px",
              lineHeight: 1.55,
              color: "#cbd5e1"
            }}
          >
            {currentStep.description}
          </p>

          {/* Action Hint Banner */}
          {currentStep.actionHint && (
            <div
              style={{
                background: "rgba(6, 182, 212, 0.12)",
                borderLeft: "3px solid #06b6d4",
                padding: "7px 10px",
                borderRadius: "0 6px 6px 0",
                fontSize: "11px",
                fontWeight: 600,
                color: "#38bdf8"
              }}
            >
              {currentStep.actionHint}
            </div>
          )}
        </div>

        {/* Card Footer with Buttons */}
        <div
          style={{
            padding: "10px 16px 14px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(10, 15, 29, 0.4)",
            borderTop: "1px solid rgba(255, 255, 255, 0.06)"
          }}
        >
          {/* Progress Dots */}
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {steps.map((_, idx) => (
              <div
                key={idx}
                style={{
                  width: idx === stepIndex ? "16px" : "6px",
                  height: "6px",
                  borderRadius: "3px",
                  background: idx === stepIndex ? "#06b6d4" : idx < stepIndex ? "#10b981" : "rgba(255,255,255,0.2)",
                  transition: "all 0.2s ease"
                }}
              />
            ))}
          </div>

          {/* Navigation Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {stepIndex > 0 && (
              <button
                type="button"
                onClick={handleBack}
                style={{
                  padding: "6px 12px",
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "#cbd5e1",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                ← Back
              </button>
            )}

            <button
              type="button"
              onClick={handleNext}
              style={{
                padding: "7px 16px",
                background: "linear-gradient(135deg, #06b6d4 0%, #0284c7 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 2px 10px rgba(6, 182, 212, 0.4)",
                display: "flex",
                alignItems: "center",
                gap: "5px"
              }}
            >
              <span>{stepIndex === steps.length - 1 ? "Complete Tour" : "Next Step"}</span>
              <span>{stepIndex === steps.length - 1 ? "🚀" : "→"}</span>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
