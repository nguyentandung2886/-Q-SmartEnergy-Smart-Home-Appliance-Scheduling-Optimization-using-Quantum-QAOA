import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function AnimatedBackground() {
  // Generate random floating particles (quantum nodes)
  const [nodes, setNodes] = useState([]);
  
  useEffect(() => {
    const newNodes = Array.from({ length: 20 }).map((_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 4 + 2,
      delay: Math.random() * 5,
      duration: Math.random() * 10 + 10,
    }));
    setNodes(newNodes);
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      zIndex: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
      background: 'radial-gradient(circle at 50% 0%, #1e1b4b 0%, #050511 70%)'
    }}>
      
      {/* Grid overlay for sci-fi feel */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)',
        backgroundSize: '50px 50px',
        transform: 'perspective(500px) rotateX(60deg) translateY(-100px) scale(3)',
        transformOrigin: 'top center',
        opacity: 0.3
      }} />

      {/* Floating Quantum Nodes */}
      {nodes.map(node => (
        <motion.div
          key={node.id}
          initial={{ x: `${node.x}vw`, y: `${node.y}vh`, opacity: 0 }}
          animate={{ 
            x: [`${node.x}vw`, `${(node.x + 10) % 100}vw`, `${(node.x - 10 + 100) % 100}vw`, `${node.x}vw`],
            y: [`${node.y}vh`, `${(node.y - 10 + 100) % 100}vh`, `${(node.y + 10) % 100}vh`, `${node.y}vh`],
            opacity: [0, 0.5, 1, 0.5, 0]
          }}
          transition={{
            duration: node.duration,
            repeat: Infinity,
            delay: node.delay,
            ease: "linear"
          }}
          style={{
            position: 'absolute',
            width: node.size,
            height: node.size,
            borderRadius: '50%',
            backgroundColor: '#06B6D4',
            boxShadow: '0 0 10px 2px rgba(6, 182, 212, 0.8)',
          }}
        />
      ))}

      {/* Wind Turbine SVG (Animated) */}
      <motion.svg 
        width="400" height="400" viewBox="0 0 200 200" 
        style={{ position: 'absolute', bottom: '-50px', right: '-50px', opacity: 0.15 }}
      >
        <path d="M100,100 L100,200" stroke="#10B981" strokeWidth="4" />
        <motion.g 
          animate={{ rotate: 360 }} 
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: '100px 100px' }}
        >
          <circle cx="100" cy="100" r="5" fill="#10B981" />
          <path d="M100,100 L100,20 Q110,60 100,100 Z" fill="#10B981" />
          <path d="M100,100 L169.28,140 Q130,120 100,100 Z" fill="#10B981" />
          <path d="M100,100 L30.72,140 Q70,120 100,100 Z" fill="#10B981" />
        </motion.g>
      </motion.svg>
      
      {/* Secondary Wind Turbine */}
      <motion.svg 
        width="250" height="250" viewBox="0 0 200 200" 
        style={{ position: 'absolute', bottom: '50px', right: '250px', opacity: 0.1 }}
      >
        <path d="M100,100 L100,200" stroke="#10B981" strokeWidth="3" />
        <motion.g 
          animate={{ rotate: 360 }} 
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: '100px 100px' }}
        >
          <circle cx="100" cy="100" r="4" fill="#10B981" />
          <path d="M100,100 L100,20 Q110,60 100,100 Z" fill="#10B981" />
          <path d="M100,100 L169.28,140 Q130,120 100,100 Z" fill="#10B981" />
          <path d="M100,100 L30.72,140 Q70,120 100,100 Z" fill="#10B981" />
        </motion.g>
      </motion.svg>
      
    </div>
  );
}
