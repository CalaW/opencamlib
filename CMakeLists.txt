cmake_minimum_required(VERSION 3.18...3.25)

project(OpenCAMLib LANGUAGES CXX)

set( CMAKE_SOURCE_DIR ${CMAKE_SOURCE_DIR}/src )
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_subdirectory( src )
