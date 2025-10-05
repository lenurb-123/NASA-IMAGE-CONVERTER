/* ====================================
   NASA IMAGE CONVERTER - VISUAL EFFECTS
   Effets visuels premium pour interface
   ==================================== */

// === GÉNÉRATION D'ÉTOILES ANIMÉES ===
function createStarsBackground() {
    const container = document.querySelector('.stars-background');
    if (!container) return;
    
    const starCount = 150;
    
    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        
        // Position aléatoire
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        
        // Taille aléatoire (1-3px)
        const size = Math.random() * 2 + 1;
        
        // Délai d'animation aléatoire
        const delay = Math.random() * 3;
        
        star.style.left = `${x}%`;
        star.style.top = `${y}%`;
        star.style.width = `${size}px`;
        star.style.height = `${size}px`;
        star.style.animationDelay = `${delay}s`;
        
        container.appendChild(star);
    }
}

// === PARTICULES FLOTTANTES ===
function createFloatingParticles() {
    const particles = document.querySelectorAll('.floating-particle');
    
    particles.forEach((particle, index) => {
        // Animation aléatoire
        const duration = 15 + Math.random() * 10; // 15-25s
        const delay = Math.random() * 5;
        
        particle.style.animationDuration = `${duration}s`;
        particle.style.animationDelay = `${delay}s`;
    });
}

// === EFFET DE CURSEUR LUEUR ===
function initCursorGlow() {
    const cursor = document.createElement('div');
    cursor.className = 'cursor-glow';
    cursor.style.cssText = `
        position: fixed;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0, 212, 255, 0.6) 0%, transparent 70%);
        pointer-events: none;
        z-index: 9999;
        mix-blend-mode: screen;
        transform: translate(-50%, -50%);
        transition: width 0.2s, height 0.2s;
    `;
    document.body.appendChild(cursor);
    
    let mouseX = 0, mouseY = 0;
    let cursorX = 0, cursorY = 0;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });
    
    // Animation fluide du curseur
    function animate() {
        cursorX += (mouseX - cursorX) * 0.1;
        cursorY += (mouseY - cursorY) * 0.1;
        
        cursor.style.left = cursorX + 'px';
        cursor.style.top = cursorY + 'px';
        
        requestAnimationFrame(animate);
    }
    animate();
    
    // Agrandir au hover sur éléments interactifs
    document.querySelectorAll('button, a, input, .interactive').forEach(el => {
        el.addEventListener('mouseenter', () => {
            cursor.style.width = '40px';
            cursor.style.height = '40px';
        });
        
        el.addEventListener('mouseleave', () => {
            cursor.style.width = '20px';
            cursor.style.height = '20px';
        });
    });
}

// === ANIMATION DES CARTES AU SCROLL ===
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, {
        threshold: 0.1
    });
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

// === COMPTEURS ANIMÉS ===
function animateCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    
    counters.forEach(counter => {
        const target = parseInt(counter.dataset.counter);
        const duration = 2000; // 2 secondes
        const steps = 60;
        const increment = target / steps;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, duration / steps);
    });
}

// === EFFET DE TYPING POUR LE TITRE ===
function typewriterEffect(element, text, speed = 100) {
    let i = 0;
    element.textContent = '';
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// === GLITCH EFFECT (optionnel pour le logo) ===
function glitchEffect(element) {
    const originalText = element.textContent;
    const glitchChars = '!<>-_\\/[]{}—=+*^?#________';
    
    let iteration = 0;
    const interval = setInterval(() => {
        element.textContent = originalText
            .split('')
            .map((char, index) => {
                if (index < iteration) {
                    return originalText[index];
                }
                return glitchChars[Math.floor(Math.random() * glitchChars.length)];
            })
            .join('');
        
        if (iteration >= originalText.length) {
            clearInterval(interval);
        }
        
        iteration += 1 / 3;
    }, 30);
}

// === EFFET DE PARALLAX ===
function initParallax() {
    document.addEventListener('mousemove', (e) => {
        const moveX = (e.clientX - window.innerWidth / 2) / 50;
        const moveY = (e.clientY - window.innerHeight / 2) / 50;
        
        document.querySelectorAll('.parallax-element').forEach((el, index) => {
            const depth = (index + 1) * 0.5;
            el.style.transform = `translate(${moveX * depth}px, ${moveY * depth}px)`;
        });
    });
}

// === INITIALISATION GLOBALE ===
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initialisation des effets visuels...');
    
    // Créer les étoiles
    createStarsBackground();
    
    // Initialiser le curseur lumineux
    initCursorGlow();
    
    // Animations au scroll
    initScrollAnimations();
    
    // Effet parallax
    initParallax();
    
    console.log('✅ Effets visuels chargés!');
});

// === EXPORT POUR UTILISATION EXTERNE ===
window.NASAEffects = {
    createStars: createStarsBackground,
    animateCounters,
    typewriter: typewriterEffect,
    glitch: glitchEffect
};
