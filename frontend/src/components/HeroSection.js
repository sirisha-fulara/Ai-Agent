import React, { useEffect, useRef } from 'react';
import Spline from '@splinetool/react-spline';
import googleIcon from '../assets/google.png'
import githubIcon from '../assets/github.png'
import { User } from 'lucide-react';

function HeroSplineBackground() {
    return (
        <div style={{
            position: 'relative',
            width: '100%',
            height: '100vh',
            pointerEvents: 'auto',
            overflow: 'hidden',
        }}>
            <Spline
                style={{
                    width: '100%',
                    height: '100vh',
                    pointerEvents: 'auto',
                }}
                scene="https://prod.spline.design/dJqTIQ-tE3ULUPMi/scene.splinecode"
            />
            <div
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100vh',
                    background: `
            linear-gradient(to right, rgba(0, 0, 0, 0.8), transparent 30%, transparent 70%, rgba(0, 0, 0, 0.8)),
            linear-gradient(to bottom, transparent 50%, rgba(0, 0, 0, 0.9))
          `,
                    pointerEvents: 'none',
                }}
            />
        </div>
    );
}

function ScreenshotSection({ screenshotRef }) {
    return (
        <section className="relative z-10 container mx-auto px-4 md:px-6 lg:px-8 mt-11 md:mt-12">
            <div ref={screenshotRef} className="bg-gray-900 rounded-xl overflow-hidden shadow-2xl border border-gray-700/50 w-full md:w-[80%] lg:w-[70%] mx-auto">
                <div>
                    <img
                        src="https://cdn.sanity.io/images/s6lu43cv/production-v4/13b6177b537aee0fc311a867ea938f16416e8670-3840x2160.jpg?w=3840&h=2160&q=10&auto=format&fm=jpg"
                        alt="App Screenshot"
                        className="w-full h-auto block rounded-lg mx-auto"
                    />
                </div>
            </div>
        </section>
    );
}

function HeroContent({ user, provider, onLoginGoogle, onLoginGithub, onLogout }) {
    return (
        <div className="text-white px-4 max-w-screen-xl mx-auto w-full flex flex-col lg:flex-row justify-between items-start lg:items-center py-16">

            <div className="w-full lg:w-1/2 pr-0 lg:pr-8 mb-8 lg:mb-0">
                <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-4 leading-tight tracking-wide">
                    AI That <br />Thinks With You.
                </h1>
                <div className="text-sm text-gray-300 opacity-90 mt-4">
                </div>
            </div>

            <div className="w-full lg:w-1/2 pl-0 lg:pl-8 flex flex-col items-start">
                <p className="text-base sm:text-lg opacity-80 mb-6 max-w-md">
                    Simple, smart, and built to make every task easier.
                </p>

                {user ? (
                    <div className="flex gap-3 flex-col sm:flex-row w-full sm:w-auto ">
                        <p className="text-green-500 font-semibold">
                            Logged in via {provider?.charAt(0).toUpperCase() + provider?.slice(1)} as{" "}
                            <span className="font-bold">{user.email || user.login}</span>
                        </p>
                        {/* <button
                            onClick={onLogout}
                            className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition w-full sm:w-auto"
                        >
                            Logout
                        </button> */}
                    </div>

                ) : (
                    <div className="flex pointer-events-auto flex-col sm:flex-row items-start space-y-3 sm:space-y-0 sm:space-x-3">
                        <button className="border border-white text-white font-semibold py-2 sm:py-3.5 px-6 sm:px-8 rounded-2xl transition duration-300 w-full sm:w-auto hover:bg-white hover:text-black flex" onClick={onLoginGoogle}>
                            Login with <img className=' px-1 h-7 w-7' src={googleIcon} />
                        </button>
                        <button className="pointer-events-auto bg-white text-black font-semibold py-2.5 sm:py-3.5 px-6 sm:px-8 rounded-2xl transition duration-300 hover:scale-105 flex items-center justify-center w-full sm:w-auto" onClick={onLoginGithub}>
                            Login with <img className=' px-1 w-7 h-7' src={githubIcon} />
                        </button>
                    </div>
                )}
            </div>

        </div>
    );
}

function Navbar({ user, onLogout }) {
    return (
        <nav className="fixed top-0 left-0 right-0 z-20" style={{ backgroundColor: 'rgba(13, 13, 24, 0.3)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', borderRadius: '0 0 0.75rem 0.75rem' }}>
            <div className="container mx-auto px-4 py-4 md:px-6 lg:px-8 flex items-center justify-between">
                <div className="flex items-center space-x-6 lg:space-x-8">
                    <div className="text-white" style={{ width: '32px', height: '32px' }}>
                        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path fillRule="evenodd" clipRule="evenodd" d="M16 32C24.8366 32 32 24.8366 32 16C32 7.16344 24.8366 0 16 0C7.16344 0 0 7.16344 0 16C0 24.8366 7.16344 32 16 32ZM12.4306 9.70695C12.742 9.33317 13.2633 9.30058 13.6052 9.62118L19.1798 14.8165C19.4894 15.1054 19.4894 15.5841 19.1798 15.873L13.6052 21.0683C13.2633 21.3889 12.742 21.3563 12.4306 19.9991V9.70695Z" fill="currentColor" />
                        </svg>
                    </div>
                </div>
                    {/* Logout Button (visible only if logged in) */}
                    {user && (
                        <button
                            onClick={onLogout}
                            className="bg-red-500 text-white px-4 py-2 rounded-full text-sm hover:bg-red-600 transition"
                        >
                            Logout
                        </button>
                    )}
            </div>
        </nav>
    );
}

const HeroSection = ({ user, provider, onLoginGoogle, onLoginGithub, onLogout }) => {
    const screenshotRef = useRef(null);
    const heroContentRef = useRef(null);

    useEffect(() => {
        const handleScroll = () => {
            if (screenshotRef.current && heroContentRef.current) {
                requestAnimationFrame(() => {
                    const scrollPosition = window.pageYOffset;

                    if (screenshotRef.current) {
                        screenshotRef.current.style.transform = `translateY(-${scrollPosition * 0.5}px)`;
                    }

                    const maxScroll = 400;
                    const opacity = 1 - Math.min(scrollPosition / maxScroll, 1);
                    if (heroContentRef.current) {
                        heroContentRef.current.style.opacity = opacity.toString();
                    }
                });
            }
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="relative">
            <Navbar user={user} onLogout={onLogout} />

            <div className="relative min-h-screen">
                <div className="absolute inset-0 z-0 pointer-events-auto">
                    <HeroSplineBackground />
                </div>

                <div ref={heroContentRef} style={{
                    position: 'absolute', top: 0, left: 0, width: '100%', height: '100vh',
                    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 10, pointerEvents: 'none'
                }}>

                    <HeroContent
                        user={user}
                        provider={provider}
                        onLoginGoogle={onLoginGoogle}
                        onLoginGithub={onLoginGithub}
                        onLogout={onLogout}
                    />

                </div>
            </div>

            <div className="bg-black relative z-10" style={{ marginTop: '-10vh' }}>
                {/* <ScreenshotSection screenshotRef={screenshotRef} /> */}

            </div>
        </div>
    );
};

export default HeroSection;