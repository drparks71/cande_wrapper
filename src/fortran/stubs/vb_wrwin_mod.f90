! vb_wrwin_mod.f90 - Stub replacement for Intel VB_WRWIN_MOD module
! This replaces the Visual Basic callback interface with no-ops.
! The original module defined Cray pointer-based function pointers
! to VB_WRITEWINDOW and VB_MSGBOX callbacks. Since the gfortran
! build has no VB GUI, these are replaced with dummy integers.

      MODULE VB_WRWIN_MOD
        IMPLICIT NONE
        INTEGER :: P_VB_WRITEWINDOW = 0
        INTEGER :: P_VB_MSGBOX = 0
      END MODULE VB_WRWIN_MOD
