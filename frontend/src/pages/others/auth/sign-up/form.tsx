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
import { EyeCloseIcon, EyeIcon, OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { signUpSchema, type SignUpFormData } from "./schema";

export default function SignUpFormFields() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const navigate = useNavigate();

  const signUp = useMutation({
    mutationFn: (data: SignUpFormData) =>
      apiFetch<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          name: `${data.fname} ${data.lname}`,
          email: data.email,
          password: data.password,
        }),
      }),
    onSuccess: () => {
      void navigate("/signin?registered=1");
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignUpFormData>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      fname: "",
      lname: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
    mode: "onTouched",
  });

  const handleFormSubmit = (data: SignUpFormData) => signUp.mutate(data);

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className="space-y-5"
      noValidate
    >
      {signUp.error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertTitle>Sign up failed</AlertTitle>
          <AlertDescription>{signUp.error.message}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Field data-invalid={Boolean(errors.fname)}>
          <FieldLabel className="mb-1.5 block">
            First Name <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("fname")}
            type="text"
            placeholder="Enter your first name"
            aria-invalid={errors.fname ? "true" : undefined}
          />
          <FieldError errors={[errors.fname]} />
        </Field>

        <Field data-invalid={Boolean(errors.lname)}>
          <FieldLabel className="mb-1.5 block">
            Last Name <span className="text-red-500">*</span>
          </FieldLabel>
          <Input
            {...register("lname")}
            type="text"
            placeholder="Enter your last name"
            aria-invalid={errors.lname ? "true" : undefined}
          />
          <FieldError errors={[errors.lname]} />
        </Field>
      </div>

      <Field data-invalid={Boolean(errors.email)}>
        <FieldLabel className="mb-1.5 block">
          Email <span className="text-red-500">*</span>
        </FieldLabel>
        <Input
          {...register("email")}
          type="email"
          placeholder="Enter your email"
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

      <Field data-invalid={Boolean(errors.confirmPassword)}>
        <FieldLabel className="mb-1.5 block">
          Confirm Password <span className="text-red-500">*</span>
        </FieldLabel>
        <InputGroup>
          <InputGroupInput
            {...register("confirmPassword")}
            type={showConfirmPassword ? "text" : "password"}
            placeholder="Re-enter your password"
            aria-invalid={errors.confirmPassword ? "true" : undefined}
          />
          <InputGroupAddon align="inline-end">
            <InputGroupButton
              size="icon-xs"
              onClick={() => setShowConfirmPassword((prev) => !prev)}
              aria-label={
                showConfirmPassword
                  ? "Hide confirm password"
                  : "Show confirm password"
              }
              className="text-gray-500 dark:text-gray-400"
            >
              {showConfirmPassword ? (
                <EyeIcon className="fill-current" />
              ) : (
                <EyeCloseIcon className="fill-current" />
              )}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
        <FieldError errors={[errors.confirmPassword]} />
      </Field>

      <div>
        <Button
          className="w-full"
          size="lg"
          type="submit"
          disabled={signUp.isPending}
        >
          {signUp.isPending ? "Signing Up..." : "Sign Up"}
        </Button>
      </div>
    </form>
  );
}
