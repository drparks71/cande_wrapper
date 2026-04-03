C* dllstop_stub.f - gfortran replacement for Intel/Dllstop.for
C* Writes message to stdout and stops execution.
C*
      SUBROUTINE DLLSTOP(MSG)
C
      INCLUDE 'dll_common.fi'
C
      CHARACTER*(*) MSG
      INTEGER       LENSTR
      INTEGER       LM
C
      LM = MAX(1, LENSTR(MSG))
      WRITE (*,'(A)') MSG(1:LM)
      STOP
C
      RETURN
      END
