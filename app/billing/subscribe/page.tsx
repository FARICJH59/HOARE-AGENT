"use client";

import { useEffect, useState } from "react";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ALLOWED_CHECKOUT_HOSTS = new Set(["checkout.stripe.com", "buy.stripe.com"]);

type SubscribePageProps = {
  searchParams?: {
    email?: string;
  };
};

export default function SubscribePage({ searchParams }: SubscribePageProps) {
  const [message, setMessage] = useState("Redirecting to checkout...");

  useEffect(() => {
    const user = {
      email: searchParams?.email?.trim() ?? "",
    };
    const isValidEmail = EMAIL_PATTERN.test(user.email);
    const apiBaseUrl = process.env.NEXT_PUBLIC_HOARE_API_URL?.trim() ?? "";

    if (!isValidEmail) {
      setMessage("Missing or invalid email address.");
      return;
    }

    if (!apiBaseUrl) {
      setMessage("Checkout is unavailable.");
      return;
    }

    let cancelled = false;

    const startCheckout = async () => {
      try {
        const billingApiUrl = new URL(
          "/api/billing/create-checkout-session",
          apiBaseUrl
        );
        const res = await fetch(
          billingApiUrl.toString(),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: user.email }),
          }
        );

        if (!res.ok) {
          throw new Error("Unable to create checkout session.");
        }

        const { url } = await res.json();

        if (typeof url !== "string" || !url) {
          throw new Error("Checkout URL was not returned.");
        }

        const checkoutUrl = new URL(url);

        if (
          checkoutUrl.protocol !== "https:" ||
          !ALLOWED_CHECKOUT_HOSTS.has(checkoutUrl.hostname)
        ) {
          throw new Error("Checkout URL is invalid.");
        }

        window.location.href = checkoutUrl.toString();
      } catch (error) {
        if (!cancelled) {
          setMessage(
            error instanceof Error ? error.message : "Checkout redirect failed."
          );
        }
      }
    };

    void startCheckout();
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  return <p>{message}</p>;
}
