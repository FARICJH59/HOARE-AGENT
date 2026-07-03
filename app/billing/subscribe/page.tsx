"use client";

import { useEffect } from "react";

type SubscribePageProps = {
  searchParams?: {
    email?: string;
  };
};

export default function SubscribePage({ searchParams }: SubscribePageProps) {
  useEffect(() => {
    const user = {
      email: searchParams?.email ?? "",
    };

    const startCheckout = async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_HOARE_API_URL}/api/billing/create-checkout-session`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: user.email }),
        }
      );

      const { url } = await res.json();
      window.location.href = url;
    };

    void startCheckout();
  }, [searchParams]);

  return null;
}
