import { useState, useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../services/authStore'

export default function Register() {
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { register } = useAuthStore()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirectTo = (() => {
    const r = searchParams.get('redirect')
    return r && r.startsWith('/') && !r.startsWith('//') ? r : '/'
  })()

  const passwordChecks = useMemo(() => ({
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*()\-_=+[\]{}|;:',.<>?/`~]/.test(password),
  }), [password])

  const passwordValid = passwordChecks.length && passwordChecks.uppercase && passwordChecks.digit && passwordChecks.special

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (!passwordValid) {
      setError('Password does not meet all requirements')
      return
    }

    setLoading(true)

    try {
      await register(email, username, password)
      navigate(redirectTo)
    } catch (err: any) {
      if (!err.response && (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED')) {
        setError('Cannot reach the server. It may be starting up — please try again in a moment.')
      } else {
        setError(err.response?.data?.detail || 'Registration failed')
      }
    } finally {
      setLoading(false)
    }
  }

  const checkClass = (met: boolean) =>
    met ? 'text-green-600' : 'text-gray-400'

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h1 className="text-center text-3xl font-bold text-gray-900">
          United Degenerates League
        </h1>
        <h2 className="mt-6 text-center text-2xl font-semibold text-gray-700">
          Create your account
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input mt-1"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Username
              </label>
              <input
                id="username"
                type="text"
                required
                minLength={3}
                maxLength={50}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input mt-1"
                placeholder="3–50 characters"
                autoComplete="username"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input mt-1"
                autoComplete="new-password"
              />
              {password.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-xs">
                  <li className={checkClass(passwordChecks.length)}>
                    {passwordChecks.length ? '✓' : '○'} At least 8 characters
                  </li>
                  <li className={checkClass(passwordChecks.uppercase)}>
                    {passwordChecks.uppercase ? '✓' : '○'} One uppercase letter
                  </li>
                  <li className={checkClass(passwordChecks.digit)}>
                    {passwordChecks.digit ? '✓' : '○'} One digit
                  </li>
                  <li className={checkClass(passwordChecks.special)}>
                    {passwordChecks.special ? '✓' : '○'} One special character
                  </li>
                </ul>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input mt-1"
                autoComplete="new-password"
              />
              {confirmPassword.length > 0 && password !== confirmPassword && (
                <p className="text-xs text-red-500 mt-1">Passwords do not match</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !passwordValid}
              className="btn btn-primary w-full"
            >
              {loading ? 'Creating account...' : 'Sign up'}
            </button>

            <div className="text-center text-sm">
              <span className="text-gray-600">Already have an account? </span>
              <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
                Sign in
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
