import { useEffect, useRef } from 'react';

export default function QuantumReactor({ phase }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    let width, height, cx, cy;
    let particles = [];
    let animationFrameId;
    let mouse = { x: -1000, y: -1000, radius: 150 };

    const init = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      cx = width / 2;
      cy = height / 2;
      particles = [];
      const numParticles = width < 768 ? 600 : 1500;
      for (let i = 0; i < numParticles; i++) {
        particles.push(new Particle());
      }
    };

    class Particle {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 1.5;
        this.vy = (Math.random() - 0.5) * 1.5;
        this.baseSize = Math.random() * 2 + 0.5;
        this.size = this.baseSize;
        this.color = Math.random() > 0.5 ? '#06B6D4' : '#10B981'; // Quantum Cyan or Energy Green
        // Grid target
        this.tx = 0;
        this.ty = 0;
      }

      update(phase) {
        // Chaos Phase (default)
        if (phase === 'chaos' || phase === 'fade') {
          // Wander randomly
          this.x += this.vx;
          this.y += this.vy;
          
          // Wrap around edges
          if (this.x < 0) this.x = width;
          if (this.x > width) this.x = 0;
          if (this.y < 0) this.y = height;
          if (this.y > height) this.y = 0;

          // Mouse repel
          let dx = mouse.x - this.x;
          let dy = mouse.y - this.y;
          let dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            this.vx -= (dx / dist) * force * 0.5;
            this.vy -= (dy / dist) * force * 0.5;
          }

          // Friction
          this.vx *= 0.98;
          this.vy *= 0.98;
          // Minimum speed
          if (Math.abs(this.vx) < 0.2) this.vx += (Math.random() - 0.5) * 0.5;
          if (Math.abs(this.vy) < 0.2) this.vy += (Math.random() - 0.5) * 0.5;
          
          this.size = this.baseSize;
        }

        // Vortex Phase (Optimizing)
        if (phase === 'vortex') {
          const dx = cx - this.x;
          const dy = cy - this.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          // Spiral inwards
          const angle = Math.atan2(dy, dx);
          const force = 2000 / (dist + 100);
          
          this.vx += Math.cos(angle) * force * 0.02;
          this.vy += Math.sin(angle) * force * 0.02;
          
          // Tangential force for vortex
          this.vx += Math.cos(angle + Math.PI / 2) * 0.5;
          this.vy += Math.sin(angle + Math.PI / 2) * 0.5;

          this.x += this.vx;
          this.y += this.vy;

          // Strong friction
          this.vx *= 0.95;
          this.vy *= 0.95;
          
          this.size = this.baseSize * (1 + 50/Math.max(dist, 10)); // Glow near center
        }

        // Grid Phase (Optimized result)
        if (phase === 'grid') {
          // Snap to target grid positions
          // Assign grid targets dynamically if not set
          if (!this.tx) {
            const cols = Math.floor(Math.sqrt(particles.length * (width/height)));
            const rows = Math.floor(particles.length / cols) + 1;
            const idx = particles.indexOf(this);
            const c = idx % cols;
            const r = Math.floor(idx / cols);
            const spacingX = width / cols;
            const spacingY = height / rows;
            this.tx = c * spacingX + spacingX / 2 + (Math.random() - 0.5) * 10;
            this.ty = r * spacingY + spacingY / 2 + (Math.random() - 0.5) * 10;
          }

          const dx = this.tx - this.x;
          const dy = this.ty - this.y;
          
          // Spring force to target
          this.vx += dx * 0.05;
          this.vy += dy * 0.05;
          
          this.x += this.vx;
          this.y += this.vy;
          
          // Friction to settle
          this.vx *= 0.85;
          this.vy *= 0.85;
          
          // Pulsing size
          this.size = this.baseSize * (1 + Math.sin(Date.now() * 0.005 + this.x) * 0.5);
        } else {
           // Reset targets when not in grid phase
           this.tx = 0;
           this.ty = 0;
        }
      }

      draw() {
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        
        // Glow effect for large particles
        if (this.size > this.baseSize * 1.5) {
            ctx.shadowBlur = 10;
            ctx.shadowColor = this.color;
            ctx.fill();
            ctx.shadowBlur = 0; // reset
        }
      }
    }

    const animate = () => {
      // Clear with trail effect
      ctx.fillStyle = phase === 'vortex' ? 'rgba(5, 5, 17, 0.2)' : 'rgba(5, 5, 17, 0.4)';
      ctx.fillRect(0, 0, width, height);

      particles.forEach(p => {
        p.update(phase);
        p.draw();
      });

      // Draw "Core" if in vortex phase
      if (phase === 'vortex') {
         const time = Date.now() * 0.005;
         const coreRadius = 40 + Math.sin(time) * 10;
         ctx.beginPath();
         ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
         ctx.fillStyle = `rgba(6, 182, 212, ${0.3 + Math.sin(time*2)*0.2})`;
         ctx.shadowBlur = 50 + Math.random()*20;
         ctx.shadowColor = '#06B6D4';
         ctx.fill();
         ctx.shadowBlur = 0;
         
         // Rings
         ctx.strokeStyle = `rgba(16, 185, 129, ${0.5 - (time%2)/2})`;
         ctx.lineWidth = 2;
         ctx.beginPath();
         ctx.arc(cx, cy, 40 + (time%2)*100, 0, Math.PI * 2);
         ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    const handleResize = () => init();
    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    
    init();
    animate();

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, [phase]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0, // Behind the UI
        pointerEvents: 'none', // Let clicks pass through to UI
      }}
    />
  );
}
