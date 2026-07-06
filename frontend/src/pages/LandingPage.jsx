import React from "react";
import LandingNavbar from "../components/landing/LandingNavbar";
import HeroSection from "../components/landing/HeroSection";
import TrustedBy from "../components/landing/TrustedBy";
import WhyBelvio from "../components/landing/WhyBelvio";
import HowItWorks from "../components/landing/HowItWorks";
import FeaturesSection from "../components/landing/FeaturesSection";
import DashboardPreview from "../components/landing/DashboardPreview";
import StatsSection from "../components/landing/StatsSection";
import InterviewDemo from "../components/landing/InterviewDemo";
import SecuritySection from "../components/landing/SecuritySection";
import Testimonials from "../components/landing/Testimonials";
import FAQ from "../components/landing/FAQ";
import Footer from "../components/landing/Footer";

export default function LandingPage({ onLoginClick }) {
  return (
    <div style={{ fontFamily: "var(--font-body)", color: "#fff", background: "#0F172A", minHeight: "100vh", overflowX: "hidden" }}>
      <LandingNavbar onLoginClick={onLoginClick} />
      <HeroSection onLoginClick={onLoginClick} />
      <TrustedBy />
      <WhyBelvio />
      <HowItWorks />
      <FeaturesSection />
      <DashboardPreview />
      <StatsSection />
      <InterviewDemo />
      <SecuritySection />
      <Testimonials />
      <FAQ />
      <Footer onLoginClick={onLoginClick} />
    </div>
  );
}
