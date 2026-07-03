"use client";

import { useEffect, useState } from "react";

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
    const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(user.email);

    if (!isValidEmail) {
      setMessage("Missing or invalid email address.");
      return;
    }

    let cancelled = false;

    const startCheckout = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_HOARE_API_URL}/api/billing/create-checkout-session`,
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

        window.location.href = url;
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
