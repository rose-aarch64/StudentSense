import { useId, useState, type FormEvent } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { intl } from "@/i18n/intl"

import { canvasErrorText } from "./canvas-error-text"
import { useConnect } from "./use-canvas"

/** The school's address and an access token: all Canvas needs to be read. */
export function ConnectForm() {
  const addressId = useId()
  const tokenId = useId()
  const [address, setAddress] = useState("")
  const [token, setToken] = useState("")
  const connect = useConnect()
  const incomplete = address.trim() === "" || token.trim() === ""

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (incomplete) return
    connect.mutate(
      { base_url: address.trim(), token: token.trim() },
      // Gone from the form the moment it has been used.
      { onSuccess: () => setToken("") }
    )
  }

  return (
    <form onSubmit={submit}>
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor={addressId}>
            {intl.formatMessage({
              id: "canvas_connect_address_label",
              defaultMessage: "School’s Canvas address",
            })}
          </FieldLabel>
          <Input
            id={addressId}
            value={address}
            onChange={(event) => setAddress(event.target.value)}
            placeholder={intl.formatMessage({
              id: "canvas_connect_address_placeholder",
              defaultMessage: "yourschool.instructure.com",
            })}
            autoComplete="off"
          />
        </Field>
        <Field>
          <FieldLabel htmlFor={tokenId}>
            {intl.formatMessage({
              id: "canvas_connect_token_label",
              defaultMessage: "Access token",
            })}
          </FieldLabel>
          <Input
            id={tokenId}
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            autoComplete="off"
          />
          <FieldDescription>
            {intl.formatMessage({
              id: "canvas_connect_token_body",
              defaultMessage:
                "Create one in Canvas under Account › Settings › New Access Token. It is stored encrypted on this computer.",
            })}
          </FieldDescription>
        </Field>
        {connect.error ? (
          <Alert variant="destructive">
            <AlertDescription>
              {canvasErrorText(connect.error)}
            </AlertDescription>
          </Alert>
        ) : null}
        <div>
          <Button type="submit" disabled={incomplete || connect.isPending}>
            {connect.isPending ? <Spinner data-icon="inline-start" /> : null}
            {intl.formatMessage({
              id: "canvas_connect_button",
              defaultMessage: "Connect",
            })}
          </Button>
        </div>
      </FieldGroup>
    </form>
  )
}
