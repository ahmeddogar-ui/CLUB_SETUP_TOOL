import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { useAuth } from "@/contexts";
import {
  CheckCircleIcon,
  EyeCloseIcon,
  EyeIcon,
  OctagonAlertIcon,
} from "@/icons";
import { apiFetch } from "@/lib/api";
import type { LoginResponse } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { signInSchema, type SignInFormData } from "./schema";

export default function SignInFormFields() {
  const [showPassword, setShowPassword] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const login = useMutation({
    mutationFn: (data: SignInFormData) =>
      apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: new URLSearchParams({
          username: data.email,
          password: data.password,
        }),
      }),
    onSuccess: (response) => {
      signIn(response.access_token);
      void navigate("/");
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInFormData>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      email: "",
      password: "",
    },
    mode: "onTouched",
  });

  const handleFormSubmit = (data: SignInFormData) => login.mutate(data);

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="space-y-5"
      noValidate
    >
      {searchParams.has("registered") && !login.error && (
        <Alert variant="success" className="p-4">
          <CheckCircleIcon className="size-5" />
          <AlertTitle>Account created</AlertTitle>
          <AlertDescription>
            Sign in with your new email and password.
          </AlertDescription>
        </Alert>
      )}
      {login.error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertTitle>Sign in failed</AlertTitle>
          <AlertDescription>{login.error.message}</AlertDescription>
        </Alert>
      )}

      <Field data-invalid={Boolean(errors.email)}>
        <FieldLabel className="mb-1.5 block">
          Email <span className="text-red-500">*</span>
        </FieldLabel>
        <Input
          {...register("email")}
          type="email"
          placeholder="info@gmail.com"
          aria-invalid={errors.email ? "true" : undefined}
        />
        <FieldError errors={[errors.email]} />
      </Field>

      <Field data-invalid={Boolean(errors.password)}>
        <FieldLabel className="mb-1.5 block">
          Password <span className="text-red-500">*</span>
        </FieldLabel>
        <InputGroup>
          <InputGroupInput
            {...register("password")}
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            aria-invalid={errors.password ? "true" : undefined}
          />
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              size="icon-xs"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="text-gray-500 dark:text-gray-400"
            >
              {showPassword ? (
                <EyeIcon className="fill-current" />
              ) : (
                <EyeCloseIcon className="fill-current" />
              )}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
        <FieldError errors={[errors.password]} />
      </Field>

      <div>
        <Button
          className="w-full"
          size="lg"
          type="submit"
          disabled={login.isPending}
        >
          {login.isPending ? "Signing In..." : "Sign In"}
        </Button>
      </div>
    </form>
  );
}
