/**
 * One message per sign-in failure reason, phrased as what the reader should
 * do next. Reason codes come from `ERROR_*` in `app/api/v1/sso.py`.
 *
 * `not_authorized` matters most: until OIT adds someone to a group it is what
 * everyone sees, and it has to read as "you're not set up yet", not "the app
 * is broken".
 */
export interface SignInMessage {
  heading: string;
  body: string;
}

export const SIGN_IN_FALLBACK: SignInMessage = {
  heading: "Sign-in didn't complete",
  body: 'Something went wrong on the way back from the University sign-in page. Please try again.',
};

const MESSAGES: Record<string, SignInMessage> = {
  not_authorized: {
    heading: "You're not set up for this app yet",
    body:
      'Your University sign-in worked, but your account has not been given access to '
      + 'the newsletter tools. Ask UCM to have you added, then try again.',
  },
  unavailable: {
    heading: 'Sign-in is temporarily unavailable',
    body:
      "We couldn't confirm your access with the University directory. This is usually "
      + 'brief. Please try again in a few minutes.',
  },
  misconfigured: {
    heading: "Sign-in isn't set up correctly",
    body:
      "The app couldn't check your access because it has not been granted permission "
      + "to read University directory groups. Retrying won't help; this needs an "
      + 'administrator.',
  },
  no_account: {
    heading: "We couldn't read your University account",
    body: 'Sign-in did not return an email address for your account. Please contact UCM.',
  },
  sign_in_failed: SIGN_IN_FALLBACK,
};

/** Look up a reason code, falling back for unknown (or prototype-polluting) keys. */
export function signInMessageFor(reason: string | null): SignInMessage {
  // Own keys only: `constructor` would otherwise read an inherited property.
  if (reason !== null && Object.prototype.hasOwnProperty.call(MESSAGES, reason)) {
    return MESSAGES[reason];
  }
  return SIGN_IN_FALLBACK;
}
