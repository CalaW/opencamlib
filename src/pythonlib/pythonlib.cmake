if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
  message(STATUS "CMake version < 3.12.0")
  find_package(PythonInterp)
  if (PYTHONINTERP_FOUND)
    if (UNIX AND NOT APPLE)
      find_package(Boost COMPONENTS python${PYTHON_VERSION_SUFFIX} REQUIRED)
      if (PYTHON_VERSION_MAJOR EQUAL 3)
          find_package(PythonInterp 3)
          find_package(PythonLibs 3 REQUIRED)
      else()
          find_package(PythonInterp)
          find_package(PythonLibs REQUIRED)
      endif()
    else()
      find_package(Boost COMPONENTS python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR} REQUIRED)
      if (PYTHON_VERSION_MAJOR EQUAL 3)
          find_package(PythonInterp 3)
          find_package(PythonLibs 3 REQUIRED)
      else()
          find_package(PythonInterp)
          find_package(PythonLibs REQUIRED)
      endif()
    endif()
  else()
    message("Python not found")
  endif()
  execute_process(
    COMMAND ${PYTHON_EXECUTABLE} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(0,0,\"/usr/local\")"
    OUTPUT_VARIABLE PYTHON_SITE_PACKAGES_RAW
    OUTPUT_STRIP_TRAILING_WHITESPACE
  ) # on Ubuntu 11.10 this outputs: /usr/local/lib/python2.7/dist-packages
  execute_process(
    COMMAND ${PYTHON_EXECUTABLE} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(plat_specific=1,standard_lib=0,prefix=\"/usr/local\")"
    OUTPUT_VARIABLE PYTHON_ARCH_PACKAGES_RAW
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  file(TO_CMAKE_PATH "${PYTHON_SITE_PACKAGES_RAW}" PYTHON_SITE_PACKAGES)
  file(TO_CMAKE_PATH "${PYTHON_ARCH_PACKAGES_RAW}" PYTHON_ARCH_PACKAGES)
else()
  message(STATUS "CMake version >= 3.12.0")
  if (USE_PY_3)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
    set(PYTHON_INCLUDE_DIRS ${Python3_INCLUDE_DIRS})
    set(PYTHON_LIBRARIES ${Python3_LIBRARIES})
    file(TO_CMAKE_PATH "${Python3_SITELIB}" PYTHON_SITE_PACKAGES)
    file(TO_CMAKE_PATH "${Python3_SITEARCH}" PYTHON_ARCH_PACKAGES)
    find_package(Boost COMPONENTS python${Python3_VERSION_MAJOR}${Python3_VERSION_MINOR} REQUIRED)
  else()
    find_package(Python2 COMPONENTS Interpreter Development REQUIRED)
    set(PYTHON_INCLUDE_DIRS ${Python2_INCLUDE_DIRS})
    set(PYTHON_LIBRARIES ${Python2_LIBRARIES})
    file(TO_CMAKE_PATH "${Python2_SITELIB}" PYTHON_SITE_PACKAGES)
    file(TO_CMAKE_PATH "${Python2_SITEARCH}" PYTHON_ARCH_PACKAGES)
    find_package(Boost COMPONENTS python${Python2_VERSION_MAJOR}${Python2_VERSION_MINOR} REQUIRED)
  endif()
endif()

message(STATUS "Boost_INCLUDE_DIR = ${Boost_INCLUDE_DIR}")
message(STATUS "Boost_INCLUDE_DIRS = ${Boost_INCLUDE_DIRS}")
message(STATUS "Boost_LIBRARY_DIRS = ${Boost_LIBRARY_DIRS}")
message(STATUS "Boost_LIBRARIES = ${Boost_LIBRARIES}")
message(STATUS "PYTHON_INCLUDE_DIRS = ${PYTHON_INCLUDE_DIRS}")
message(STATUS "PYTHON_LIBRARIES = ${PYTHON_LIBRARIES}")
message(STATUS "PYTHON_SITE_PACKAGES = ${PYTHON_SITE_PACKAGES}")
message(STATUS "PYTHON_ARCH_PACKAGES = ${PYTHON_ARCH_PACKAGES}")

include_directories(${Boost_INCLUDE_DIRS})
include_directories(${PYTHON_INCLUDE_DIRS})

# include dirs
include_directories(${OpenCamLib_SOURCE_DIR}/cutters)
include_directories(${OpenCamLib_SOURCE_DIR}/geo)
include_directories(${OpenCamLib_SOURCE_DIR}/algo)
include_directories(${OpenCamLib_SOURCE_DIR}/dropcutter)
include_directories(${OpenCamLib_SOURCE_DIR}/common)
include_directories(${OpenCamLib_SOURCE_DIR})

# this makes the ocl Python module
add_library(
  ocl 
  MODULE
  pythonlib/ocl_cutters.cpp
  pythonlib/ocl_geometry.cpp
  pythonlib/ocl_algo.cpp
  pythonlib/ocl_dropcutter.cpp
  pythonlib/ocl.cpp
)

target_link_libraries(
  ocl
  ocl_common
  ocl_dropcutter
  ocl_cutters
  ocl_geo
  ocl_algo
  ${Boost_LIBRARIES}
  ${OpenMP_CXX_LIBRARIES}
)

if(APPLE)
  # to avoid the need to link with libpython, we should use dynamic lookup
  set_target_properties(ocl PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
else()
  target_link_libraries(ocl ${PYTHON_LIBRARIES})
endif()

set_target_properties(ocl PROPERTIES PREFIX "")

# this makes the lib name ocl.pyd and not ocl.so
if (WIN32)
  set_target_properties(ocl PROPERTIES SUFFIX ".pyd")
endif (WIN32)

# when a custom prefix is given, use it (ugly hack)
if(
  (UNIX AND NOT "${CMAKE_INSTALL_PREFIX}" STREQUAL "/usr/local")
  OR (WIN32
    AND NOT "${CMAKE_INSTALL_PREFIX}" STREQUAL "C:/Program Files/${PROJECT_NAME}"
    AND NOT "${CMAKE_INSTALL_PREFIX}" STREQUAL "C:/Program Files (x86)/${PROJECT_NAME}"
    AND NOT "${CMAKE_INSTALL_PREFIX}" STREQUAL "C:/Program Files (Arm)/${PROJECT_NAME}"
  )
)
  set(PYTHON_SITE_PACKAGES "${CMAKE_INSTALL_PREFIX}")
  set(PYTHON_ARCH_PACKAGES "${CMAKE_INSTALL_PREFIX}")
endif()

if(USE_OPENMP AND APPLE)
  # copy libomp into install directory
  install(
    FILES ${OpenMP_omp_LIBRARY}
    DESTINATION "${PYTHON_SITE_PACKAGES}"
    PERMISSIONS OWNER_READ GROUP_READ WORLD_READ
  )
  # fix loader path
  add_custom_command(TARGET ocl POST_BUILD
    COMMAND ${CMAKE_INSTALL_NAME_TOOL} -change `otool -L $<TARGET_FILE:ocl> | grep libomp | cut -d ' ' -f1 | xargs echo` "@loader_path/libomp.dylib" $<TARGET_FILE:ocl>
  )
endif()

install(
  TARGETS ocl
  LIBRARY DESTINATION "${PYTHON_ARCH_PACKAGES}"
)

# these are the python helper lib-files such as camvtk.py 
install(
  DIRECTORY lib/
  DESTINATION "${PYTHON_SITE_PACKAGES}"
)