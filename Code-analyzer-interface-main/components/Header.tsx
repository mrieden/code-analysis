import React from 'react';
import { Page } from '../types';
import GradientText from './GradientText';
import ThemeToggle from './ThemeToggle';
// Note: The 'useTheme' hook is no longer needed in this simplified file.

interface HeaderProps {
    onNavigate: (page: Page) => void;
}

// The complex AuraOwlLensLogo SVG component has been completely removed.

const Header: React.FC<HeaderProps> = ({ onNavigate }) => {
    return (
        <header className="bg-ui-panels/50 backdrop-blur-sm border-b border-border-color sticky top-0 z-10">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-20">
                    <div className="flex items-center cursor-pointer" onClick={() => onNavigate(Page.DASHBOARD)}>

                        {/* The SVG component is now replaced with a simple <img> tag */}
                        <img
                            src="/logo.png"
                            alt="Code Analyzer Logo"
                            className="h-20 w-20 mr-4"
                        />

                        <div>
                            <GradientText as="h1" className="text-2xl font-bold tracking-wider">Strivora AI</GradientText>
                            <p className="text-sm text-text-secondary tracking-widest">See Beyond Syntax</p>
                        </div>
                    </div>
                    <nav className="flex items-center space-x-4 md:space-x-8">
                        <button
                            onClick={() => onNavigate(Page.ABOUT)}
                            className="text-text-primary hover:text-accent-primary transition-colors duration-200 text-lg font-medium"
                        >
                            About
                        </button>
                        <button
                            onClick={() => onNavigate(Page.HELP)}
                            className="text-text-primary hover:text-accent-primary transition-colors duration-200 text-lg font-medium"
                        >
                            Help
                        </button>
                        <ThemeToggle />
                    </nav>
                </div>
            </div>
        </header>
    );
};

export default Header;
